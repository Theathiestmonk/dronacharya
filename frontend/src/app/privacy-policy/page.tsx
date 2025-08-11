import React from 'react';
import LeftPanel from '../components/LeftPanel';

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen h-screen">
      <div className="fixed left-0 top-0 h-screen z-10">
        <LeftPanel />
      </div>
      <main className="ml-20 h-screen overflow-y-auto block">
        <div className="max-w-3xl w-full py-12 px-4 text-gray-900 mx-auto text-justify" style={{ paddingTop: '90px' }}>
          <h1 className="text-3xl font-bold mb-6">Privacy Policy</h1>
          <p className="mb-4">At Prakriti, we value your privacy and are committed to protecting your personal information. This Privacy Policy explains how we collect, use, and disclose your data when you use our website or services. We may collect information such as contact details, demographic data, and usage information to improve our services and provide a personalized experience. We may share your information with trusted third parties for specific purposes. We have implemented security measures to protect your data, but please note that no method is 100% secure. By using our website or services, you agree to the terms of this Privacy Policy.</p>

          <h2 className="text-2xl font-semibold mt-8 mb-2">Information We Collect (Collection and Sharing of Customer Information)</h2>
          <p className="mb-2">We may collect personal information from you when you voluntarily provide it to us through forms, surveys, or other interactions on our website. The types of personal information we may collect include:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>Contact Information: Your name, email address, phone number, and mailing address.</li>
            <li>Demographic Information: Your age, gender, and location.</li>
            <li>Student Information: If you are a student, we may collect information such as your student ID, grade level, and class schedule.</li>
            <li>Login Information: Usernames, passwords, and security questions for accessing certain areas or services on our website.</li>
            <li>Usage Information: Information about how you use our website, including IP address, browser type, device information, and browsing activities.</li>
          </ul>
          <p className="mb-4">Information is collected only with the explicit agreement of the visitor and is processed securely for the purpose of ensuring hassle-free product shipment. Collected information may include title, name, gender, email address, postal address, delivery address (if different), telephone number, mobile number, fax number, payment details, or bank account details.</p>
          <p className="mb-4">Actual order details may be securely stored, and visitors can access this information by logging into their accounts on the site. Visitors undertake to treat personal access data confidentially and refrain from making it available to unauthorized third parties. Under no circumstances is personal information rented, traded, or shared for marketing purposes without visitor consent. However, https://prakriti.edu.in/ reserves the right to communicate personal information to any third party making a legally compliant request for its disclosure.</p>

          <h2 className="text-2xl font-semibold mt-8 mb-2">Use of Information</h2>
          <p className="mb-2">We use the collected information for the following purposes:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>To provide and improve our services.</li>
            <li>To respond to inquiries, feedback, or requests.</li>
            <li>To personalize your experience and deliver tailored content.</li>
            <li>To send you administrative information, such as updates or changes to our policies.</li>
            <li>To analyze trends, track usage patterns, and gather demographic information for research and statistical purposes.</li>
            <li>To protect against unauthorized access, fraud, or other unlawful activities.</li>
          </ul>

          <h2 className="text-2xl font-semibold mt-8 mb-2">Changes to This Privacy Policy</h2>
          <p className="mb-4">We may update this Privacy Policy from time to time. The updated version will be posted on our website, and the "Last Updated" date at the top will reflect the changes. By continuing to use our website or services after any changes to this policy, you acknowledge and agree to the updated terms.</p>

          <h2 className="text-2xl font-semibold mt-8 mb-2">Intellectual Property Rights</h2>
          <p>All content included on this site, such as text, graphics, logos, button icons, images, and software, is the property of PRAKRITI. All content not owned by PRAKRITI is used with permission.</p>
        </div>
      </main>
    </div>
  );
} 