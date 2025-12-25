import React from 'react';
import LeftPanel from '../components/LeftPanel';

export default function TermsOfService() {
  return (
    <div className="min-h-screen h-screen">
      <div className="fixed left-0 top-0 h-screen z-10">
        <LeftPanel />
      </div>
      <main className="ml-20 h-screen overflow-y-auto block">
        <div className="max-w-4xl w-full py-12 px-4 text-gray-900 mx-auto text-justify" style={{ paddingTop: '90px' }}>
          <h1 className="text-3xl font-bold mb-6">Terms of Service for Prakriti Chatbot</h1>
          <p className="mb-4 text-sm text-gray-600">Last Updated: December 24, 2024</p>

          <p className="mb-6">
            Welcome to Prakriti Chatbot (&quot;Service&quot;), an AI-powered educational assistant provided by Prakriti School (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;). These Terms of Service (&quot;Terms&quot;) govern your access to and use of the Prakriti Chatbot, website, and related services. By accessing or using our Service, you agree to be bound by these Terms. If you disagree with any part of these Terms, you may not access the Service.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">1. Service Description</h2>

          <p className="mb-4">
            Prakriti Chatbot is an AI-powered educational assistant designed to support students, parents, teachers, and administrators at Prakriti School. Our Service provides:
          </p>
          <ul className="list-disc pl-6 mb-4">
            <li>Educational information and school-related queries</li>
            <li>Homework assistance and academic support</li>
            <li>Lesson planning and curriculum guidance</li>
            <li>Grading assistance and feedback</li>
            <li>Integration with Google Classroom and educational tools</li>
            <li>YouTube educational content recommendations</li>
            <li>Web-enhanced responses for comprehensive information</li>
            <li>Administrative support and school management tools</li>
          </ul>

          <h2 className="text-2xl font-semibold mt-8 mb-4">2. Eligibility and User Accounts</h2>

          <h3 className="text-xl font-medium mt-6 mb-3">2.1 Eligibility Requirements</h3>
          <p className="mb-3">To use our Service, you must:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>Be associated with Prakriti School as a student, parent, teacher, or administrator</li>
            <li>Be at least 13 years old (or have parental consent if younger)</li>
            <li>Provide accurate and complete registration information</li>
            <li>Maintain the security of your account credentials</li>
            <li>Comply with all applicable laws and school policies</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">2.2 Account Registration and Security</h3>
          <p className="mb-4">
            You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account. You must immediately notify us of any unauthorized use of your account or any other breach of security.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">2.3 Parental Consent for Minors</h3>
          <p className="mb-4">
            Students under 18 years of age require parental or guardian consent to create an account and use our Service. Parents are responsible for supervising their child's use of the Service and ensuring compliance with these Terms.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">3. Acceptable Use Policy</h2>

          <h3 className="text-xl font-medium mt-6 mb-3">3.1 Permissible Use</h3>
          <p className="mb-3">You may use our Service only for lawful educational purposes, including:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>Seeking educational assistance and information about Prakriti School</li>
            <li>Completing homework assignments and academic tasks</li>
            <li>Accessing curriculum-related resources and materials</li>
            <li>Communicating with teachers and school administrators</li>
            <li>Participating in school-related discussions and activities</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">3.2 Prohibited Activities</h3>
          <p className="mb-3">You must not use our Service to:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>Violate any applicable laws, regulations, or school policies</li>
            <li>Share inappropriate, offensive, or harmful content</li>
            <li>Attempt to gain unauthorized access to other users' accounts or data</li>
            <li>Use the Service for commercial purposes without authorization</li>
            <li>Harass, bully, or intimidate other users</li>
            <li>Share confidential or sensitive information inappropriately</li>
            <li>Attempt to reverse engineer, hack, or compromise the Service</li>
            <li>Use automated tools or bots to access the Service</li>
            <li>Impersonate other individuals or entities</li>
            <li>Engage in academic dishonesty or cheating</li>
          </ul>

          <h2 className="text-2xl font-semibold mt-8 mb-4">4. AI Limitations and Disclaimers</h2>

          <h3 className="text-xl font-medium mt-6 mb-3">4.1 AI-Generated Content</h3>
          <p className="mb-4">
            Our Service uses artificial intelligence to generate responses and provide assistance. While we strive for accuracy and educational value, AI-generated content may contain errors, inaccuracies, or outdated information. You should always verify critical information through official school channels.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">4.2 No Professional Advice</h3>
          <p className="mb-4">
            The Service is not a substitute for professional educational, medical, legal, or psychological advice. Always consult qualified professionals for matters requiring expert judgment or specialized knowledge.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">4.3 Service Availability</h3>
          <p className="mb-4">
            We strive to maintain high availability of our Service but cannot guarantee uninterrupted access. The Service may be temporarily unavailable due to maintenance, technical issues, or unforeseen circumstances.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">5. Educational Content and Academic Integrity</h2>

          <h3 className="text-xl font-medium mt-6 mb-3">5.1 Academic Honesty</h3>
          <p className="mb-4">
            Students are expected to use the Service ethically and maintain academic integrity. The Service should support learning, not circumvent it. Teachers and administrators may monitor usage to ensure compliance with academic standards.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">5.2 Content Ownership</h3>
          <p className="mb-4">
            All educational content, curriculum materials, and school-related information provided through the Service remain the property of Prakriti School. Users may not reproduce, distribute, or use this content for unauthorized purposes.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">5.3 Google Classroom Integration</h3>
          <p className="mb-4">
            When integrating with Google Classroom, you authorize us to access your educational data as necessary to provide our services. This integration is subject to Google's Terms of Service and Privacy Policy.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">6. Intellectual Property Rights</h2>

          <h3 className="text-xl font-medium mt-6 mb-3">6.1 Our Intellectual Property</h3>
          <p className="mb-4">
            The Service and its original content, features, and functionality are owned by Prakriti School and are protected by copyright, trademark, and other intellectual property laws. This includes our AI models, algorithms, user interface, and educational content.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">6.2 User-Generated Content</h3>
          <p className="mb-4">
            By submitting content to our Service, you grant us a non-exclusive, royalty-free, perpetual, and worldwide license to use, modify, and incorporate such content into our Service for educational purposes. You retain ownership of your original content but grant us the rights necessary to provide our services.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">6.3 Third-Party Content</h3>
          <p className="mb-4">
            Our Service may integrate with or display content from third parties, including YouTube videos and web resources. Such content is subject to the respective third parties' terms of service and intellectual property rights.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">7. Privacy and Data Protection</h2>

          <p className="mb-4">
            Your privacy is important to us. Our collection and use of personal information is governed by our Privacy Policy, which is incorporated into these Terms by reference. By using our Service, you consent to the collection, use, and sharing of your information as described in our Privacy Policy.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">8. Termination and Suspension</h2>

          <h3 className="text-xl font-medium mt-6 mb-3">8.1 Termination by User</h3>
          <p className="mb-4">
            You may terminate your account at any time by contacting us or using the account deletion features in the Service. Upon termination, your right to use the Service will cease immediately.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">8.2 Termination by Us</h3>
          <p className="mb-4">
            We may terminate or suspend your account and access to the Service immediately, without prior notice or liability, for any reason, including but not limited to breach of these Terms, violation of school policies, or illegal activity.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">8.3 Effect of Termination</h3>
          <p className="mb-4">
            Upon termination, your access to the Service will be disabled, and we may delete your account and associated data. Sections of these Terms that by their nature should survive termination will remain in effect.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">9. Disclaimers and Limitation of Liability</h2>

          <h3 className="text-xl font-medium mt-6 mb-3">9.1 Service Disclaimer</h3>
          <p className="mb-4">
            The Service is provided on an &quot;as is&quot; and &quot;as available&quot; basis. We make no warranties, expressed or implied, regarding the Service's accuracy, reliability, suitability, or availability.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">9.2 Limitation of Liability</h3>
          <p className="mb-4">
            To the fullest extent permitted by law, Prakriti School shall not be liable for any indirect, incidental, special, consequential, or punitive damages arising out of or related to your use of the Service.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">9.3 Educational Outcomes</h3>
          <p className="mb-4">
            We do not guarantee specific educational outcomes or academic success. The Service is a supplementary tool and should not replace traditional teaching methods or professional educational guidance.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">10. Indemnification</h2>

          <p className="mb-4">
            You agree to defend, indemnify, and hold harmless Prakriti School, its officers, directors, employees, and agents from and against any claims, damages, losses, liabilities, costs, and expenses arising out of or related to your use of the Service, violation of these Terms, or violation of any rights of another party.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">11. Modifications to Terms</h2>

          <p className="mb-4">
            We reserve the right to modify these Terms at any time. We will notify users of material changes through the Service or by email. Your continued use of the Service after such modifications constitutes acceptance of the updated Terms.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">12. Governing Law and Dispute Resolution</h2>

          <h3 className="text-xl font-medium mt-6 mb-3">12.1 Governing Law</h3>
          <p className="mb-4">
            These Terms shall be governed by and construed in accordance with the laws of India, specifically the laws applicable in the National Capital Territory of Delhi, without regard to its conflict of law provisions.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">12.2 Dispute Resolution</h3>
          <p className="mb-4">
            Any disputes arising out of or relating to these Terms or the Service shall be resolved through amicable negotiations. If negotiations fail, disputes shall be subject to the exclusive jurisdiction of the courts in Gautam Buddha Nagar, Uttar Pradesh, India.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">13. Severability</h2>

          <p className="mb-4">
            If any provision of these Terms is found to be unenforceable or invalid, that provision will be limited or eliminated to the minimum extent necessary so that the Terms will otherwise remain in full force and effect.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">14. Entire Agreement</h2>

          <p className="mb-4">
            These Terms, together with our Privacy Policy, constitute the entire agreement between you and Prakriti School regarding the use of the Service and supersede all prior agreements or understandings.
          </p>

          <h2 className="text-2xl font-semibold mt-8 mb-4">15. Contact Information</h2>

          <p className="mb-3">If you have any questions about these Terms, please contact us:</p>

          <div className="bg-gray-50 p-4 rounded-lg mb-6">
            <p className="mb-2"><strong>Prakriti School</strong></p>
            <p className="mb-2">Noida Expressway, Greater Noida</p>
            <p className="mb-2">Delhi NCR, India</p>
            <p className="mb-2">Email: legal@prakriti.edu.in</p>
            <p className="mb-2">Phone: [Contact Number]</p>
            <p className="mb-2">Website: https://prakriti.edu.in</p>
          </div>

          <p className="mb-4">
            For educational inquiries, please contact our academic office at academics@prakriti.edu.in.
          </p>

          <p className="text-sm text-gray-600 mt-8">
            These Terms of Service are designed to comply with applicable laws including Indian contract law, education regulations, and consumer protection laws. Last reviewed: December 24, 2024.
          </p>
        </div>
      </main>
    </div>
  );
}

