import type { NextApiRequest, NextApiResponse } from 'next';
import { createClient } from '@supabase/supabase-js';

const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { email } = req.body;

    if (!email || typeof email !== 'string') {
      return res.status(400).json({ error: 'Student email is required' });
    }

    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      supabaseServiceKey
    );

    // Find student profile by email
    const { data: profile, error: profileError } = await supabase
      .from('user_profiles')
      .select('user_id, role')
      .eq('email', email)
      .eq('role', 'student')
      .single();

    if (profileError || !profile) {
      return res.status(404).json({ error: 'Student profile not found' });
    }

    // Get OAuth connection
    const { data: connection, error: connError } = await supabase
      .from('google_oauth_connections')
      .select('access_token, refresh_token, token_expires_at')
      .eq('user_id', profile.user_id)
      .eq('service', 'classroom')
      .eq('is_active', true)
      .single();

    if (connError || !connection) {
      return res.status(404).json({ error: 'Google Classroom not connected' });
    }

    // Check if token needs refresh
    let accessToken = connection.access_token;
    const expiresAt = connection.token_expires_at ? new Date(connection.token_expires_at) : null;
    
    if (expiresAt && expiresAt < new Date()) {
      // Token expired, refresh it
      const refreshResponse = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          client_id: process.env.GOOGLE_CLIENT_ID!,
          client_secret: process.env.GOOGLE_CLIENT_SECRET!,
          refresh_token: connection.refresh_token!,
          grant_type: 'refresh_token'
        })
      });

      if (!refreshResponse.ok) {
        return res.status(401).json({ error: 'Failed to refresh token. Please reconnect.' });
      }

      const refreshData = await refreshResponse.json();
      accessToken = refreshData.access_token;

      // Update token in database
      await supabase
        .from('google_oauth_connections')
        .update({
          access_token: accessToken,
          token_expires_at: refreshData.expires_in
            ? new Date(Date.now() + refreshData.expires_in * 1000).toISOString()
            : null
        })
        .eq('user_id', profile.user_id)
        .eq('service', 'classroom');
    }

    // Helper function to parse Google timestamp
    function parseGoogleTimestamp(timestamp: string | undefined): string | null {
      if (!timestamp) return null;
      try {
        return new Date(timestamp).toISOString();
      } catch {
        return null;
      }
    }

    // Fetch student's courses (only to get course IDs, not to store them)
    const coursesResponse = await fetch('https://classroom.googleapis.com/v1/courses?studentId=me', {
      headers: { Authorization: `Bearer ${accessToken}` }
    });

    if (!coursesResponse.ok) {
      return res.status(500).json({ error: 'Failed to fetch courses from Google Classroom' });
    }

    const coursesData = await coursesResponse.json();
    const courses = coursesData.courses || [];

    let syncedCoursework = 0;
    let syncedSubmissions = 0;

    // Process each course - only fetch coursework and submissions for this student
    for (const course of courses) {
      // Find existing course from admin sync (don't create new course)
      // Courses are stored by admin, so we look for any course with this course_id
      const { data: existingCourses, error: courseError } = await supabase
        .from('google_classroom_courses')
        .select('id, course_id')
        .eq('course_id', course.id)
        .limit(1);

      // If course doesn't exist in admin sync, create it for this student (fallback)
      let courseDbId;
      if (!existingCourses || existingCourses.length === 0 || courseError) {
        console.log(`Course ${course.id} not found in admin sync. Creating course record for student...`);
        
        // Create course record for this student (fallback if admin sync hasn't run)
        const { data: newCourse, error: createError } = await supabase
          .from('google_classroom_courses')
          .insert({
            user_id: profile.user_id,
            course_id: course.id,
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
            last_synced_at: new Date().toISOString()
          })
          .select('id')
          .single();

        if (createError || !newCourse) {
          console.error(`Failed to create course ${course.id}:`, createError);
          continue; // Skip this course if we can't create it
        }
        courseDbId = newCourse.id;
      } else {
        courseDbId = existingCourses[0].id;
      }

      // Fetch coursework (assignments) assigned to this student
      const courseworkResponse = await fetch(
        `https://classroom.googleapis.com/v1/courses/${course.id}/courseWork?courseWorkStates=PUBLISHED`,
        { headers: { Authorization: `Bearer ${accessToken}` } }
      );

      if (courseworkResponse.ok) {
        const courseworkData = await courseworkResponse.json();
        const coursework = courseworkData.courseWork || [];

        for (const cw of coursework) {
          // Store coursework (this student's assignments)
          const courseworkDataToStore = {
            course_id: courseDbId,
            coursework_id: cw.id,
            title: cw.title || '',
            description: cw.description || null,
            materials: cw.materials || null,
            state: cw.state || null,
            alternate_link: cw.alternateLink || null,
            creation_time: parseGoogleTimestamp(cw.creationTime),
            update_time: parseGoogleTimestamp(cw.updateTime),
            due_date: cw.dueDate ? parseGoogleTimestamp(`${cw.dueDate.year}-${String(cw.dueDate.month).padStart(2, '0')}-${String(cw.dueDate.day).padStart(2, '0')}T00:00:00Z`) : null,
            due_time: cw.dueTime ? `${String(cw.dueTime.hours).padStart(2, '0')}:${String(cw.dueTime.minutes).padStart(2, '0')}` : null,
            max_points: cw.maxPoints ? parseFloat(cw.maxPoints) : null,
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

          // Check if coursework already exists (upsert)
          const { data: existingCw } = await supabase
            .from('google_classroom_coursework')
            .select('id')
            .eq('course_id', courseDbId)
            .eq('coursework_id', cw.id)
            .maybeSingle();

          let cwDbId;
          if (existingCw) {
            // Update existing coursework
            const { data: updatedCw, error: updateError } = await supabase
              .from('google_classroom_coursework')
              .update(courseworkDataToStore)
              .eq('id', existingCw.id)
              .select('id')
              .single();
            
            if (updateError) {
              console.error(`Error updating coursework ${cw.id}:`, updateError);
              continue;
            }
            cwDbId = updatedCw?.id;
          } else {
            // Insert new coursework
            const { data: newCw, error: insertError } = await supabase
              .from('google_classroom_coursework')
              .insert(courseworkDataToStore)
              .select('id')
              .single();
            
            if (insertError || !newCw) {
              console.error(`Error inserting coursework ${cw.id}:`, insertError);
              continue;
            }
            cwDbId = newCw.id;
          }

          if (cwDbId) {
            syncedCoursework++;

            // Fetch this student's submissions for this coursework
            const submissionsResponse = await fetch(
              `https://classroom.googleapis.com/v1/courses/${course.id}/courseWork/${cw.id}/studentSubmissions?userId=me`,
              { headers: { Authorization: `Bearer ${accessToken}` } }
            );

            if (submissionsResponse.ok) {
              const submissionsData = await submissionsResponse.json();
              const submissions = submissionsData.studentSubmissions || [];

              for (const sub of submissions) {
                // Only store this student's own submissions
                if (sub.userId && sub.userId !== profile.user_id) {
                  continue; // Skip if not this student's submission
                }

                // Store submission (only for this student)
                const submissionData = {
                  coursework_id: cwDbId,
                  submission_id: sub.id || '',
                  course_id: course.id,
                  coursework_id_google: cw.id,
                  user_id: sub.userId || profile.user_id,
                  state: sub.state || null,
                  alternate_link: sub.alternateLink || null,
                  assigned_grade: sub.assignedGrade ? parseFloat(sub.assignedGrade) : null,
                  draft_grade: sub.draftGrade ? parseFloat(sub.draftGrade) : null,
                  course_work_type: sub.courseWorkType || null,
                  associated_with_developer: sub.associatedWithDeveloper || false,
                  submission_history: sub.submissionHistory || null,
                  last_synced_at: new Date().toISOString()
                };

                // Upsert submission
                const { data: existingSub } = await supabase
                  .from('google_classroom_submissions')
                  .select('id')
                  .eq('coursework_id', cwDbId)
                  .eq('submission_id', sub.id)
                  .maybeSingle();

                if (existingSub) {
                  const { error: updateSubError } = await supabase
                    .from('google_classroom_submissions')
                    .update(submissionData)
                    .eq('id', existingSub.id);
                  
                  if (updateSubError) {
                    console.error(`Error updating submission ${sub.id}:`, updateSubError);
                    continue;
                  }
                } else {
                  const { error: insertSubError } = await supabase
                    .from('google_classroom_submissions')
                    .insert(submissionData);
                  
                  if (insertSubError) {
                    console.error(`Error inserting submission ${sub.id}:`, insertSubError);
                    continue;
                  }
                }
                syncedSubmissions++;
              }
            }
          }
        }
      }
    }

    return res.status(200).json({
      success: true,
      message: 'Student coursework and submissions synced successfully',
      stats: {
        courses_processed: courses.length,
        coursework: syncedCoursework,
        submissions: syncedSubmissions
      }
    });
  } catch (error) {
    console.error('Error syncing classroom:', error);
    return res.status(500).json({ 
      error: 'Internal server error',
      details: error instanceof Error ? error.message : String(error)
    });
  }
}

