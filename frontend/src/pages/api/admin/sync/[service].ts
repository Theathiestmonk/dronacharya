import { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Helper function to parse Google timestamp
function parseGoogleTimestamp(timestamp: string | undefined): string | null {
  if (!timestamp) return null;
  try {
    return new Date(timestamp).toISOString();
  } catch {
    return null;
  }
}

// Helper function to extract name from Google profile
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function extractNameFromProfile(profile: { name?: { fullName?: string; givenName?: string }; emailAddress?: string }): string {
  if (!profile) return '';
  return profile.name?.fullName || profile.name?.givenName || profile.emailAddress || '';
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { service } = req.query;

  if (!service || (service !== 'classroom' && service !== 'calendar' && service !== 'website')) {
    return res.status(400).json({ error: 'Invalid service type' });
  }

  try {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      supabaseServiceKey!
    );

    const adminEmail = req.body?.adminEmail;
    console.log(`🔍 Syncing ${service} for ${adminEmail || 'NO EMAIL'}`);

    if (!adminEmail) {
      return res.status(400).json({ 
        error: 'User email is required. Please ensure you are logged in.' 
      });
    }

    // Get user profile
    const { data: userProfile } = await supabase
      .from('user_profiles')
      .select('*')
      .eq('email', adminEmail)
      .eq('is_active', true)
      .single();

    if (!userProfile || !userProfile.admin_privileges) {
      return res.status(403).json({ 
        error: 'Admin privileges required' 
      });
    }

    // IMPORTANT: Use user_id (auth.users.id) not id (user_profiles.id) for foreign key constraints
    // google_classroom_courses.user_id references auth.users(id), not user_profiles.id
    const userId = userProfile.user_id || userProfile.id; // Prefer user_id, fallback to id
    const adminId = userProfile.id; // user_profiles.id for admin_id in google_integrations
    
    console.log(`🔍 Found user profile:`, { 
      profile_id: adminId, 
      auth_user_id: userId,
      email: adminEmail 
    });

    // Get integration - use admin_id (user_profiles.id) not user_id (auth.users.id)
    const { data: integrations } = await supabase
      .from('google_integrations')
      .select('*')
      .eq('admin_id', adminId) // admin_id references user_profiles.id
      .eq('service_type', service)
      .eq('is_active', true)
      .limit(1);
    
    if (!integrations || integrations.length === 0) {
      return res.status(400).json({ 
        error: `No active ${service} integration found. Please connect first.` 
      });
    }

    const integration = integrations[0];
    
    // Check if token needs refresh
    let accessToken = integration.access_token;
    const expiresAt = integration.token_expires_at ? new Date(integration.token_expires_at) : null;
    
    // Refresh token if expired or about to expire (within 5 minutes)
    if (expiresAt && (expiresAt < new Date() || expiresAt < new Date(Date.now() + 5 * 60 * 1000))) {
      console.log(`🔄 Token expired or expiring soon, refreshing...`);
      
      if (!integration.refresh_token) {
        return res.status(401).json({ 
          error: 'Token expired and no refresh token available. Please reconnect your Google account.' 
        });
      }
      
      try {
        const refreshResponse = await fetch('https://oauth2.googleapis.com/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({
            client_id: process.env.GOOGLE_CLIENT_ID!,
            client_secret: process.env.GOOGLE_CLIENT_SECRET!,
            refresh_token: integration.refresh_token,
            grant_type: 'refresh_token'
          })
        });

        if (!refreshResponse.ok) {
          const errorText = await refreshResponse.text();
          console.error('Token refresh failed:', errorText);
          return res.status(401).json({ 
            error: 'Failed to refresh token. Please reconnect your Google account.' 
          });
        }

        const refreshData = await refreshResponse.json();
        accessToken = refreshData.access_token;
        
        // Calculate new expiration time
        const newExpiresAt = refreshData.expires_in
          ? new Date(Date.now() + refreshData.expires_in * 1000).toISOString()
          : null;

        // Update token in database
        const { error: updateError } = await supabase
          .from('google_integrations')
          .update({
            access_token: accessToken,
            token_expires_at: newExpiresAt,
            updated_at: new Date().toISOString()
          })
          .eq('id', integration.id);

        if (updateError) {
          console.error('Failed to update token in database:', updateError);
          // Continue with new token even if DB update fails
        } else {
          console.log('✅ Token refreshed and saved to database');
        }
      } catch (error) {
        console.error('Error refreshing token:', error);
        return res.status(500).json({ 
          error: 'Error refreshing authentication token. Please try again.' 
        });
      }
    }

    const syncStats = {
      courses: { created: 0, updated: 0 },
      teachers: { created: 0, updated: 0 },
      students: { created: 0, updated: 0 },
      coursework: { created: 0, updated: 0 },
      submissions: { created: 0, updated: 0 },
      announcements: { created: 0, updated: 0 },
      calendars: { created: 0, updated: 0 },
      events: { created: 0, updated: 0 }
    };
    
    if (service === 'classroom') {
      console.log(`🔍 Fetching Google Classroom data...`);
      
      // 1. Fetch courses
      const classResponse = await fetch('https://classroom.googleapis.com/v1/courses', {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });

      if (!classResponse.ok) {
        const errorData = await classResponse.text();
        return res.status(classResponse.status).json({ 
          error: `Failed to fetch courses: ${errorData}` 
        });
      }

      const classData = await classResponse.json();
      const courses = classData.courses || [];
      console.log(`🔍 Found ${courses.length} courses`);

      // Process each course
      for (const course of courses) {
        const courseId = course.id;
        console.log(`🔍 Processing course: ${course.name} (${courseId})`);
        
        // Store/update course in google_classroom_courses
        const courseData = {
          user_id: userId,
          course_id: courseId,
          name: course.name || '',
          description: course.description || null,
          section: course.section || null,
          room: course.room || null,
          owner_id: course.ownerId || null,
          enrollment_code: course.enrollmentCode || null,
          course_state: course.courseState || null,
          alternate_link: course.alternateLink || null,
          teacher_group_email: course.teacherGroupEmail || null,
          course_group_email: course.courseGroupEmail || null,
          guardians_enabled: course.guardiansEnabled || false,
          calendar_enabled: course.calendarId ? true : false,
          max_rosters: course.maxRosters || null,
          course_material_sets: course.courseMaterialSets || null,
          gradebook_settings: course.gradebookSettings || null,
          description_heading: course.descriptionHeading || null,
          update_time: parseGoogleTimestamp(course.updateTime),
          last_synced_at: new Date().toISOString()
        };

        // Upsert course
        const { data: existingCourse, error: courseError } = await supabase
          .from('google_classroom_courses')
          .select('id')
          .eq('user_id', userId)
          .eq('course_id', courseId)
          .single();

        let dbCourseId: string | null = null;

        if (courseError && courseError.code !== 'PGRST116') { // PGRST116 = not found
          console.error(`❌ Error checking course:`, courseError);
        }

        if (existingCourse) {
          // Update existing course
          const { error: updateError } = await supabase
            .from('google_classroom_courses')
            .update(courseData)
            .eq('id', existingCourse.id);
          
          if (updateError) {
            console.error(`❌ Error updating course:`, updateError);
          } else {
            dbCourseId = existingCourse.id;
            syncStats.courses.updated++;
          }
        } else {
          // Insert new course - get the ID back
          const { data: newCourse, error: insertError } = await supabase
            .from('google_classroom_courses')
            .insert(courseData)
            .select('id')
            .single();
          
          if (insertError) {
            console.error(`❌ Error inserting course:`, insertError);
          } else if (newCourse) {
            dbCourseId = newCourse.id;
            syncStats.courses.created++;
          }
        }

        // Fallback: try to get ID if we still don't have it
        if (!dbCourseId) {
          const { data: courseRecord, error: fetchError } = await supabase
            .from('google_classroom_courses')
            .select('id')
            .eq('user_id', userId)
            .eq('course_id', courseId)
            .single();
          
          if (fetchError) {
            console.error(`❌ Could not get database course ID for ${courseId}:`, fetchError);
            continue;
          }
          dbCourseId = courseRecord?.id || null;
        }

        if (!dbCourseId) {
          console.error(`❌ Could not get database course ID for ${courseId} after all attempts`);
          continue;
        }

        // 2. Fetch and store teachers
        try {
          const teachersResponse = await fetch(
            `https://classroom.googleapis.com/v1/courses/${courseId}/teachers`,
            { headers: { 'Authorization': `Bearer ${accessToken}` } }
          );
          if (teachersResponse.ok) {
            const teachersData = await teachersResponse.json();
            const teachers = teachersData.teachers || [];
            console.log(`🔍   Found ${teachers.length} teachers`);

            for (const teacher of teachers) {
              const teacherData = {
                course_id: dbCourseId,
                user_id: teacher.userId || '',
                course_user_id: teacher.courseId ? `${courseId}_${teacher.userId}` : '',
                profile: teacher.profile || {}
              };

              const { data: existingTeacher } = await supabase
                .from('google_classroom_teachers')
                .select('id')
                .eq('course_id', dbCourseId)
                .eq('course_user_id', teacherData.course_user_id)
                .single();

              if (existingTeacher) {
                const { error: updateError } = await supabase.from('google_classroom_teachers').update(teacherData).eq('id', existingTeacher.id);
                if (updateError) {
                  console.error(`❌ Error updating teacher ${teacher.userId}:`, updateError);
                } else {
                  syncStats.teachers.updated++;
                }
              } else {
                const { error: insertError } = await supabase.from('google_classroom_teachers').insert(teacherData);
                if (insertError) {
                  console.error(`❌ Error inserting teacher ${teacher.userId}:`, insertError);
                } else {
                  syncStats.teachers.created++;
                }
              }
            }
          }
        } catch (e) {
          console.log(`⚠️ Could not fetch teachers: ${e}`);
        }

        // 3. Fetch and store students
        try {
          const studentsResponse = await fetch(
            `https://classroom.googleapis.com/v1/courses/${courseId}/students`,
            { headers: { 'Authorization': `Bearer ${accessToken}` } }
          );
          if (studentsResponse.ok) {
            const studentsData = await studentsResponse.json();
            const students = studentsData.students || [];
            console.log(`🔍   Found ${students.length} students`);

            for (const student of students) {
              const studentData = {
                course_id: dbCourseId,
                user_id: student.userId || '',
                course_user_id: student.courseId ? `${courseId}_${student.userId}` : '',
                profile: student.profile || {},
                student_work_folder: student.studentWorkFolder || null
              };

              const { data: existingStudent } = await supabase
                .from('google_classroom_students')
                .select('id')
                .eq('course_id', dbCourseId)
                .eq('course_user_id', studentData.course_user_id)
                .single();

              if (existingStudent) {
                const { error: updateError } = await supabase.from('google_classroom_students').update(studentData).eq('id', existingStudent.id);
                if (updateError) {
                  console.error(`❌ Error updating student ${student.userId}:`, updateError);
                } else {
                  syncStats.students.updated++;
                }
              } else {
                const { error: insertError } = await supabase.from('google_classroom_students').insert(studentData);
                if (insertError) {
                  console.error(`❌ Error inserting student ${student.userId}:`, insertError);
                } else {
                  syncStats.students.created++;
                }
              }
            }
          }
        } catch (e) {
          console.log(`⚠️ Could not fetch students: ${e}`);
        }
        
        // 4. Fetch and store coursework
        try {
          const courseworkResponse = await fetch(
            `https://classroom.googleapis.com/v1/courses/${courseId}/courseWork`,
            { headers: { 'Authorization': `Bearer ${accessToken}` } }
          );
          if (courseworkResponse.ok) {
            const courseworkData = await courseworkResponse.json();
            const courseworkList = courseworkData.courseWork || [];
            console.log(`🔍   Found ${courseworkList.length} coursework items`);

            for (const cw of courseworkList) {
              const courseworkData = {
                course_id: dbCourseId,
                coursework_id: cw.id || '',
                title: cw.title || '',
                description: cw.description || null,
                materials: cw.materials || null,
                state: cw.state || null,
                alternate_link: cw.alternateLink || null,
                creation_time: parseGoogleTimestamp(cw.creationTime),
                update_time: parseGoogleTimestamp(cw.updateTime),
                due_date: cw.dueDate ? parseGoogleTimestamp(`${cw.dueDate.date}T00:00:00Z`) : 
                          (cw.dueTime ? parseGoogleTimestamp(cw.dueTime) : null),
                due_time: cw.dueTime || null,
                max_points: cw.maxPoints ? parseFloat(cw.maxPoints.value || '0') : null,
                work_type: cw.workType || null,
                associated_with_developer: cw.associatedWithDeveloper || false,
                assignee_mode: cw.assigneeMode || null,
                individual_students_options: cw.individualStudentsOptions || null,
                submission_modification_mode: cw.submissionModificationMode || null,
                creator_user_id: cw.creatorUserId || null,
                topic_id: cw.topicId || null,
                grade_category: cw.gradeCategory || null,
                assignment: cw.assignment || null,
                multiple_choice_question: cw.multipleChoiceQuestion || null,
                last_synced_at: new Date().toISOString()
              };

              const { data: existingCw } = await supabase
                .from('google_classroom_coursework')
                .select('id')
                .eq('course_id', dbCourseId)
                .eq('coursework_id', courseworkData.coursework_id)
                .single();

              let cwDbId;
              if (existingCw) {
                await supabase.from('google_classroom_coursework').update(courseworkData).eq('id', existingCw.id);
                cwDbId = existingCw.id;
                syncStats.coursework.updated++;
              } else {
                const { data: newCw } = await supabase.from('google_classroom_coursework').insert(courseworkData).select('id').single();
                cwDbId = newCw?.id;
                syncStats.coursework.created++;
              }

              // 5. Fetch and store submissions for this coursework
              if (cwDbId && cw.id) {
                try {
                  const submissionsResponse = await fetch(
                    `https://classroom.googleapis.com/v1/courses/${courseId}/courseWork/${cw.id}/studentSubmissions`,
                    { headers: { 'Authorization': `Bearer ${accessToken}` } }
                  );
                  if (submissionsResponse.ok) {
                    const submissionsData = await submissionsResponse.json();
                    const submissions = submissionsData.studentSubmissions || [];

                    for (const sub of submissions) {
                      const submissionData = {
                        coursework_id: cwDbId,
                        submission_id: sub.id || '',
                        course_id: courseId,
                        coursework_id_google: cw.id,
                        user_id: sub.userId || '',
                        state: sub.state || null,
                        alternate_link: sub.alternateLink || null,
                        assigned_grade: sub.assignedGrade ? parseFloat(sub.assignedGrade) : null,
                        draft_grade: sub.draftGrade ? parseFloat(sub.draftGrade) : null,
                        course_work_type: sub.courseWorkType || null,
                        associated_with_developer: sub.associatedWithDeveloper || false,
                        submission_history: sub.submissionHistory || null,
                        late: sub.late || false,
                        last_synced_at: new Date().toISOString()
                      };

                      const { data: existingSub } = await supabase
                        .from('google_classroom_submissions')
                        .select('id')
                        .eq('coursework_id', cwDbId)
                        .eq('submission_id', submissionData.submission_id)
                        .single();

                      if (existingSub) {
                        await supabase.from('google_classroom_submissions').update(submissionData).eq('id', existingSub.id);
                        syncStats.submissions.updated++;
          } else {
                        await supabase.from('google_classroom_submissions').insert(submissionData);
                        syncStats.submissions.created++;
                      }
                    }
                  }
                } catch (e) {
                  console.log(`⚠️ Could not fetch submissions: ${e}`);
                }
              }
            }
          }
        } catch (e) {
          console.log(`⚠️ Could not fetch coursework: ${e}`);
        }

        // 6. Fetch and store announcements
        try {
          const announcementsResponse = await fetch(
            `https://classroom.googleapis.com/v1/courses/${courseId}/announcements`,
            { headers: { 'Authorization': `Bearer ${accessToken}` } }
          );
          if (announcementsResponse.ok) {
            const announcementsData = await announcementsResponse.json();
            const announcements = announcementsData.announcements || [];
            console.log(`🔍   Found ${announcements.length} announcements`);

            for (const ann of announcements) {
              const announcementData = {
                course_id: dbCourseId,
                announcement_id: ann.id || '',
                text: ann.text || null,
                materials: ann.materials || null,
                state: ann.state || null,
                alternate_link: ann.alternateLink || null,
                creation_time: parseGoogleTimestamp(ann.creationTime),
                update_time: parseGoogleTimestamp(ann.updateTime),
                scheduled_time: ann.scheduledTime ? parseGoogleTimestamp(ann.scheduledTime) : null,
                assignee_mode: ann.assigneeMode || null,
                individual_students_options: ann.individualStudentsOptions || null,
                creator_user_id: ann.creatorUserId || null,
                course_work_type: ann.courseWorkType || null,
                last_synced_at: new Date().toISOString()
              };

              const { data: existingAnn } = await supabase
                .from('google_classroom_announcements')
                .select('id')
                .eq('course_id', dbCourseId)
                .eq('announcement_id', announcementData.announcement_id)
                .single();

              if (existingAnn) {
                const { error: updateError } = await supabase.from('google_classroom_announcements').update(announcementData).eq('id', existingAnn.id);
                if (updateError) {
                  console.error(`❌ Error updating announcement ${ann.id}:`, updateError);
                } else {
                  syncStats.announcements.updated++;
                }
              } else {
                const { error: insertError } = await supabase.from('google_classroom_announcements').insert(announcementData);
        if (insertError) {
                  console.error(`❌ Error inserting announcement ${ann.id}:`, insertError);
                } else {
                  syncStats.announcements.created++;
                }
              }
            }
          }
        } catch (e) {
          console.log(`⚠️ Could not fetch announcements: ${e}`);
        }
      }

      // Log final stats
      console.log(`🔍 ✅ Sync completed! Stats:`, {
        courses: `${syncStats.courses.created} created, ${syncStats.courses.updated} updated`,
        teachers: `${syncStats.teachers.created} created, ${syncStats.teachers.updated} updated`,
        students: `${syncStats.students.created} created, ${syncStats.students.updated} updated`,
        announcements: `${syncStats.announcements.created} created, ${syncStats.announcements.updated} updated`,
        coursework: `${syncStats.coursework.created} created, ${syncStats.coursework.updated} updated`,
        submissions: `${syncStats.submissions.created} created, ${syncStats.submissions.updated} updated`
      });

      return res.status(200).json({
        success: true,
        message: `Synced Google Classroom data successfully`,
        stats: {
          courses: syncStats.courses,
          teachers: syncStats.teachers,
          students: syncStats.students,
          announcements: syncStats.announcements,
          coursework: syncStats.coursework,
          submissions: syncStats.submissions
        },
        summary: {
          courses: syncStats.courses.created + syncStats.courses.updated,
          teachers: syncStats.teachers.created + syncStats.teachers.updated,
          students: syncStats.students.created + syncStats.students.updated,
          announcements: syncStats.announcements.created + syncStats.announcements.updated,
          coursework: syncStats.coursework.created + syncStats.coursework.updated,
          submissions: syncStats.submissions.created + syncStats.submissions.updated
        }
      });

    } else { // calendar
      console.log(`🔍 Fetching Google Calendar data...`);

      // 1. Fetch calendars list
      const calendarsResponse = await fetch('https://www.googleapis.com/calendar/v3/users/me/calendarList', {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });

      const calendars = calendarsResponse.ok ? (await calendarsResponse.json()).items || [] : [];
      console.log(`🔍 Found ${calendars.length} calendars`);

      for (const cal of calendars) {
        const calendarData = {
          user_id: userId,
          calendar_id: cal.id || '',
          summary: cal.summary || null,
          description: cal.description || null,
          location: cal.location || null,
          timezone: cal.timeZone || null,
          color_id: cal.colorId || null,
          background_color: cal.backgroundColor || null,
          foreground_color: cal.foregroundColor || null,
          access_role: cal.accessRole || null,
          selected: cal.selected !== false,
          primary_calendar: cal.primary || false,
          deleted: cal.deleted || false,
          conference_properties: cal.conferenceProperties || null,
          notification_settings: cal.notificationSettings || null,
          last_synced_at: new Date().toISOString()
        };

        const { data: existingCal } = await supabase
          .from('google_calendar_calendars')
          .select('id')
          .eq('user_id', userId)
          .eq('calendar_id', calendarData.calendar_id)
          .single();

        if (existingCal) {
          await supabase.from('google_calendar_calendars').update(calendarData).eq('id', existingCal.id);
          syncStats.calendars.updated++;
        } else {
          await supabase.from('google_calendar_calendars').insert(calendarData);
          syncStats.calendars.created++;
        }
      }

      // 2. Fetch events from primary calendar (and selected calendars)
      const timeMin = new Date().toISOString();
      const timeMax = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString();

      const calendarsToSync = calendars.filter((cal: { selected?: boolean; primary?: boolean }) => cal.selected !== false || cal.primary);
      if (calendarsToSync.length === 0 && calendars.length > 0) {
        calendarsToSync.push(calendars[0]); // At least sync primary
      }

      for (const cal of calendarsToSync) {
        const calId = cal.id || 'primary';
        console.log(`🔍 Fetching events from calendar: ${calId}`);

        const eventsResponse = await fetch(
          `https://www.googleapis.com/calendar/v3/calendars/${calId}/events?timeMin=${timeMin}&timeMax=${timeMax}&singleEvents=true&orderBy=startTime`,
        { headers: { 'Authorization': `Bearer ${accessToken}` } }
      );

        if (!eventsResponse.ok) continue;

        const eventsData = await eventsResponse.json();
        const events = eventsData.items || [];
        console.log(`🔍   Found ${events.length} events`);

        for (const event of events) {
          const startDateTime = event.start?.dateTime || event.start?.date;
          const endDateTime = event.end?.dateTime || event.end?.date;

          const eventData = {
            user_id: userId,
            event_id: event.id || '',
            calendar_id: calId,
            summary: event.summary || null,
            description: event.description || null,
            location: event.location || null,
            start_time: startDateTime ? parseGoogleTimestamp(startDateTime) : null,
            end_time: endDateTime ? parseGoogleTimestamp(endDateTime) : null,
            all_day: !event.start?.dateTime && !!event.start?.date,
            timezone: event.start?.timeZone || null,
            recurrence: event.recurrence || null,
            attendees: event.attendees || null,
            creator: event.creator || null,
            organizer: event.organizer || null,
            html_link: event.htmlLink || null,
            hangout_link: event.hangoutLink || (event.conferenceData?.entryPoints?.find((ep: { entryPointType?: string; uri?: string }) => ep.entryPointType === 'video')?.uri || null),
            conference_data: event.conferenceData || null,
            visibility: event.visibility || null,
            transparency: event.transparency || null,
            status: event.status || null,
            event_type: event.eventType || null,
            color_id: event.colorId || null,
            last_synced_at: new Date().toISOString()
          };

          const { data: existingEvent } = await supabase
            .from('google_calendar_events')
            .select('id')
            .eq('user_id', userId)
            .eq('event_id', eventData.event_id)
            .single();

          if (existingEvent) {
            await supabase.from('google_calendar_events').update(eventData).eq('id', existingEvent.id);
            syncStats.events.updated++;
          } else {
            await supabase.from('google_calendar_events').insert(eventData);
            syncStats.events.created++;
          }
        }
      }

      // Log final stats
      console.log(`🔍 ✅ Calendar sync completed! Stats:`, {
        calendars: `${syncStats.calendars.created} created, ${syncStats.calendars.updated} updated`,
        events: `${syncStats.events.created} created, ${syncStats.events.updated} updated`
      });

      return res.status(200).json({
        success: true,
        message: `Synced Google Calendar data successfully`,
        stats: {
          calendars: syncStats.calendars,
          events: syncStats.events
        },
        summary: {
          calendars: syncStats.calendars.created + syncStats.calendars.updated,
          events: syncStats.events.created + syncStats.events.updated
        }
      });
    }

    // Website sync - clear cache and trigger fresh crawl
    if (service === 'website') {
      console.log(`🔍 Starting website data sync (clearing cache and re-crawling)...`);
      
      try {
        // Call backend API to refresh web crawler cache
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const syncResponse = await fetch(`${backendUrl}/api/admin/sync/website`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            adminEmail: adminEmail
          }),
        });

        if (!syncResponse.ok) {
          const errorData = await syncResponse.text();
          return res.status(syncResponse.status).json({ 
            error: `Failed to sync website data: ${errorData}` 
          });
        }

        const syncData = await syncResponse.json();
        
        return res.status(200).json({
          success: true,
          message: syncData.message || 'Website data synced successfully',
          stats: syncData.stats || {},
          summary: syncData.summary || {}
        });
      } catch (error: unknown) {
        console.error('❌ Error in website sync:', error);
        const errorDetails = error instanceof Error ? (error as Error).message : String(error);
        return res.status(500).json({
          error: 'Failed to sync website data',
          details: errorDetails
        });
      }
    }

  } catch (error: unknown) {
    console.error(`❌ Error syncing ${service}:`, error);
    const errorMessage = error instanceof Error ? (error as Error).message : 'Unknown error';
    return res.status(500).json({ 
      error: 'Internal server error',
      details: errorMessage 
    });
  }
}




















