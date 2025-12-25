import React from 'react';
import LeftPanel from '../components/LeftPanel';

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen h-screen">
      <div className="fixed left-0 top-0 h-screen z-10">
        <LeftPanel />
      </div>
      <main className="ml-20 h-screen overflow-y-auto block">
        <div className="max-w-4xl w-full py-12 px-4 text-gray-900 mx-auto text-justify" style={{ paddingTop: '90px' }}>
          <h1 className="text-3xl font-bold mb-6">Privacy Policy for Prakriti Chatbot</h1>
          <p className="mb-4 text-sm text-gray-600">Last Updated: December 24, 2024</p>

          <p className="mb-6">
            Prakriti School (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;) operates the Prakriti Chatbot, an AI-powered educational assistant designed to support students, parents, teachers, and administrators at Prakriti School. This Privacy Policy describes how we collect, use, disclose, and safeguard your information when you use our chatbot services, website, and related educational platforms.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">1. Information We Collect</h2>

          <h3 className="text-xl font-medium mt-6 mb-3">1.1 Personal Information</h3>
          <p className="mb-3">We collect personal information that you voluntarily provide to us when you:</p>
          <ul className="list-disc pl-6 mb-4">
            <li><strong>Registration and Profile Creation:</strong> Name, email address, phone number, student/teacher/administrator status, grade level, and profile preferences.</li>
            <li><strong>Chat Interactions:</strong> Messages, queries, and responses exchanged through the chatbot interface.</li>
            <li><strong>Educational Data:</strong> Student grades, assignment submissions, coursework details, attendance records, and academic performance data (when integrated with Google Classroom or other educational systems).</li>
            <li><strong>Google Integration:</strong> When you connect your Google account for Classroom integration, we access your Google profile information, classroom data, and coursework submissions.</li>
            <li><strong>Feedback and Support:</strong> Information provided when you contact us for support or provide feedback about our services.</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">1.2 Automatically Collected Information</h3>
          <p className="mb-3">We automatically collect certain information when you use our services:</p>
          <ul className="list-disc pl-6 mb-4">
            <li><strong>Device Information:</strong> IP address, browser type, operating system, device identifiers, and screen resolution.</li>
            <li><strong>Usage Data:</strong> Chat session logs, feature usage patterns, response times, error logs, and interaction timestamps.</li>
            <li><strong>Cookies and Tracking:</strong> We use cookies and similar technologies to enhance your experience and analyze service usage.</li>
            <li><strong>Performance Metrics:</strong> System performance data, AI model response accuracy, and service reliability metrics.</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">1.3 Third-Party Integrations</h3>
          <p className="mb-3">Our chatbot integrates with third-party services including:</p>
          <ul className="list-disc pl-6 mb-4">
            <li><strong>Google Classroom:</strong> Coursework, assignments, grades, and student submissions.</li>
            <li><strong>YouTube:</strong> Educational video content and recommendations.</li>
            <li><strong>Web Services:</strong> Educational resources and web content for enhanced responses.</li>
            <li><strong>Supabase:</strong> Database services for storing user profiles and chat history.</li>
          </ul>

          <h2 className="text-2xl font-semibold mt-8 mb-4">2. How We Use Your Information</h2>

          <p className="mb-3">We use the collected information for the following educational and operational purposes:</p>
          <ul className="list-disc pl-6 mb-4">
            <li><strong>Educational Support:</strong> Providing personalized learning assistance, homework help, and academic guidance.</li>
            <li><strong>Chatbot Functionality:</strong> Processing queries, generating responses, and maintaining conversation context.</li>
            <li><strong>Personalization:</strong> Customizing responses based on your role (student, teacher, parent, administrator) and academic level.</li>
            <li><strong>Progress Tracking:</strong> Monitoring student engagement, learning patterns, and educational outcomes.</li>
            <li><strong>Administrative Functions:</strong> Managing user accounts, providing technical support, and ensuring system security.</li>
            <li><strong>Service Improvement:</strong> Analyzing usage patterns to enhance AI responses, fix issues, and develop new educational features.</li>
            <li><strong>Compliance and Safety:</strong> Ensuring compliance with educational standards, preventing misuse, and maintaining a safe learning environment.</li>
            <li><strong>Communication:</strong> Sending important updates, maintenance notifications, and educational announcements.</li>
          </ul>

          <h2 className="text-2xl font-semibold mt-8 mb-4">3. Information Sharing and Disclosure</h2>

          <h3 className="text-xl font-medium mt-6 mb-3">3.1 Educational Sharing</h3>
          <p className="mb-3">Within the Prakriti School community:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>Teachers may access student chat history and usage data for educational purposes.</li>
            <li>Administrators may review system usage analytics for school management.</li>
            <li>Parents may access their child's usage data and educational progress information.</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">3.2 Service Providers</h3>
          <p className="mb-3">We share information with trusted service providers who assist us in:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>AI and machine learning services (OpenAI, Google AI)</li>
            <li>Database and hosting services (Supabase)</li>
            <li>Analytics and performance monitoring</li>
            <li>Security and compliance services</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">3.3 Legal Requirements</h3>
          <p className="mb-4">
            We may disclose information when required by law, court order, or government regulation, or when necessary to protect the rights, property, or safety of Prakriti School, our users, or the public.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">3.4 No Sale of Personal Information</h3>
          <p className="mb-4">
            We do not sell, rent, or lease your personal information to third parties for marketing purposes. Your educational data remains within the Prakriti School ecosystem.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">4. Data Security</h2>

          <p className="mb-3">We implement comprehensive security measures to protect your information:</p>
          <ul className="list-disc pl-6 mb-4">
            <li><strong>Encryption:</strong> All data transmission is encrypted using SSL/TLS protocols.</li>
            <li><strong>Access Controls:</strong> Role-based access controls ensure users only access appropriate information.</li>
            <li><strong>Secure Storage:</strong> Educational data is stored in secure, compliant databases with regular backups.</li>
            <li><strong>Regular Audits:</strong> Security audits and vulnerability assessments are conducted regularly.</li>
            <li><strong>Incident Response:</strong> We have procedures in place to respond to security incidents and data breaches.</li>
            <li><strong>Employee Training:</strong> Staff receive training on data protection and privacy practices.</li>
          </ul>

          <p className="mb-4">
            While we strive to protect your information, no method of transmission over the internet or electronic storage is 100% secure. We cannot guarantee absolute security.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">5. Children's Privacy (COPPA Compliance)</h2>

          <p className="mb-4">
            Prakriti Chatbot serves students of various ages at Prakriti School. We are committed to complying with the Children's Online Privacy Protection Act (COPPA) and similar regulations:
          </p>
          <ul className="list-disc pl-6 mb-4">
            <li>Students under 13 require parental consent for account creation and use.</li>
            <li>Parents have the right to review, modify, or delete their child's personal information.</li>
            <li>Educational data collection is limited to what is necessary for learning purposes.</li>
            <li>We do not collect personal information from children under 13 without verifiable parental consent.</li>
            <li>Parents can contact us at any time to exercise their rights regarding their child's data.</li>
          </ul>

          <h2 className="text-2xl font-semibold mt-8 mb-4">6. Data Retention</h2>

          <p className="mb-3">We retain your information for the following periods:</p>
          <ul className="list-disc pl-6 mb-4">
            <li><strong>Chat History:</strong> Educational chat sessions are retained for up to 2 years for learning analytics and support purposes.</li>
            <li><strong>User Profiles:</strong> Account information is retained while your account is active and for a reasonable period after account closure.</li>
            <li><strong>Educational Data:</strong> Academic records and performance data may be retained longer as required by educational regulations.</li>
            <li><strong>Usage Logs:</strong> System logs are retained for 1 year for security and troubleshooting purposes.</li>
          </ul>

          <p className="mb-4">
            You may request deletion of your data at any time, subject to legal and educational record-keeping requirements.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">7. Your Rights and Choices</h2>

          <p className="mb-3">Depending on your location, you may have the following rights regarding your personal information:</p>
          <ul className="list-disc pl-6 mb-4">
            <li><strong>Access:</strong> Request a copy of the personal information we hold about you.</li>
            <li><strong>Correction:</strong> Request correction of inaccurate or incomplete information.</li>
            <li><strong>Deletion:</strong> Request deletion of your personal information (subject to legal requirements).</li>
            <li><strong>Portability:</strong> Request transfer of your data in a structured format.</li>
            <li><strong>Opt-out:</strong> Opt out of certain data processing activities.</li>
            <li><strong>Restriction:</strong> Request limitation of how we process your information.</li>
          </ul>

          <p className="mb-4">
            To exercise these rights, please contact us using the information provided below.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">8. Cookies and Tracking Technologies</h2>

          <p className="mb-3">We use cookies and similar technologies to:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>Maintain your session and login status</li>
            <li>Remember your preferences and settings</li>
            <li>Analyze usage patterns and improve our services</li>
            <li>Ensure security and prevent fraud</li>
          </ul>

          <p className="mb-4">
            You can control cookie settings through your browser preferences. However, disabling certain cookies may affect the functionality of our services.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">9. International Data Transfers</h2>

          <p className="mb-4">
            Our services are primarily hosted in India and the United States. If you are accessing our services from outside these regions, your information may be transferred to, processed, and stored in these locations. We ensure appropriate safeguards are in place for such transfers, including standard contractual clauses and adequacy decisions.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">10. Third-Party Links and Services</h2>

          <p className="mb-4">
            Our chatbot may provide links to third-party websites or integrate with external services (such as YouTube). This Privacy Policy does not apply to these external services. We encourage you to review the privacy policies of any third-party services you use.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">11. Changes to This Privacy Policy</h2>

          <p className="mb-4">
            We may update this Privacy Policy from time to time to reflect changes in our practices, technology, legal requirements, or other factors. We will notify you of material changes by:
          </p>
          <ul className="list-disc pl-6 mb-4">
            <li>Posting the updated policy on our website</li>
            <li>Sending an email notification (where applicable)</li>
            <li>Providing an in-app notification</li>
          </ul>

          <p className="mb-4">
            Your continued use of our services after changes become effective constitutes acceptance of the updated Privacy Policy.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">12. Contact Us</h2>

          <p className="mb-3">If you have questions about this Privacy Policy or our data practices, please contact us:</p>

          <div className="bg-gray-50 p-4 rounded-lg mb-6">
            <p className="mb-2"><strong>Prakriti School</strong></p>
            <p className="mb-2">Noida Expressway, Greater Noida</p>
            <p className="mb-2">Delhi NCR, India</p>
            <p className="mb-2">Email: privacy@prakriti.edu.in</p>
            <p className="mb-2">Phone: [Contact Number]</p>
            <p className="mb-2">Website: https://prakriti.edu.in</p>
          </div>

          <p className="mb-4">
            For data protection inquiries specific to EU users, you may also contact our Data Protection Officer at dpo@prakriti.edu.in.
          </p>

          <p className="text-sm text-gray-600 mt-8">
            This Privacy Policy is designed to comply with applicable data protection laws including GDPR, COPPA, and Indian data protection regulations. Last reviewed: December 24, 2024.
          </p>
        </div>
      </main>
    </div>
  );
} 