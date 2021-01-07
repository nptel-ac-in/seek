function parseJSONP(main,text) {
  var prefix = ")]}'\n";
  var error = Polymer.dom(main.parentElement.parentElement).querySelector('.server-error');
  if (text.indexOf(prefix) === 0) {
    var parsedText = text.substring(prefix.length);
    var response = JSON.parse(parsedText);
    if (response.status == 200)
    {
      if (error) error.style.display = "none";
      return JSON.parse(response.payload);
    }
    else if (response.status == 401){
      if (error) error.style.display = "none";
      window.location = JSON.parse(response.payload).loginurl;
    }
    else{
      if (error)
      {
        error.style.display = "block";
        // error.innerHTML = "The Request has failed with error"+response.status+" because "+response.message;
        error.innerHTML = "<div>Oops, something's wrong. Please try again in sometime.</div><div>Details: " + response.status + " : " + response.message + "</div>";
      }
    }
  }
}

function validateResponse(main,response) {
  var spinner = Polymer.dom(main.root).querySelector('paper-spinner-lite');
  if(response.ok)
    {
      spinner.active = false;
      spinner.style.display = "none";
      response.text().then(obj => {
        return main.processResponse(parseJSONP(main,obj));
      });
    }
  else {
      spinner.active = false;
      spinner.style.display = "none";
      console.log(response);
    }
}

function b64DecodeUnicode(str) {
    // Going backwards: from bytestream, to percent-encoding, to original string.
    return decodeURIComponent(atob(str).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
}

function showSpinnerHideError(main)
{
  var spinner = Polymer.dom(main.root).querySelector('paper-spinner-lite');
  var error = Polymer.dom(main.parentElement.parentElement).querySelector('.server-error');
  error.style.display = "none";
  spinner.active = true;
  spinner.style.display = "block";
}

function showErrorHideSpinner(main,message)
{
  var spinner = Polymer.dom(main.root).querySelector('paper-spinner-lite');
  var error = Polymer.dom(main.parentElement.parentElement).querySelector('.server-error');
  spinner.active = false;
  spinner.style.display = "none";
  error.style.display = "block";
  error.innerHTML = message;
}

function logError(error) {
  console.log('Looks like there was a problem: \n', error);
}

// Firebase
const FIREBASE_SENDER_ID = "539841117281";
const FIREBASE_PUBLIC_KEY = "BPeaeXIqjezF-DCWr_HoE78pRvJ0iXyUdNCypw-bj2qXE1uRVgBm0Z8lAwpdmN5QVjLHlfyS6Zz6x-77QlFPsPA";
const FIREBASE_SW_URL = "/modules/pwa/_static/nptel-pwa/assets/js/firebase-messaging-sw.js";
var config = {
  messagingSenderId: FIREBASE_SENDER_ID,
};
firebase.initializeApp(config);
const messaging = firebase.messaging();

// Initialize service worker
messaging.usePublicVapidKey(FIREBASE_PUBLIC_KEY);
navigator.serviceWorker.register(FIREBASE_SW_URL)
.then((registration) => {
  messaging.useServiceWorker(registration);
});

function loadPushToken() {
  var token = localStorage.getItem("push_token");
  return token?token:'';
}

function savePushToken(token) {
  localStorage.setItem("push_token", token)
}

function registerNewPushToken(callback) {
  // `callback` is called only when a NEW push token is registered.
  messaging.requestPermission().then(function() {
    messaging.getToken().then(function(currentToken) {
      var oldToken = loadPushToken();
      savePushToken(currentToken);
      if ((oldToken !== currentToken) && callback) {
        callback();
      }
    });
  }).catch(function(err) {
    console.log('Unable to get permission to notify.', err);
    var notif = localStorage.getItem("first_alert");
    if (!notif)
    {
      alert('Notifications might not work for you');
      localStorage.setItem("first_alert",true);
    }

  });
}
// Callback fired if Instance ID token is updated.
messaging.onTokenRefresh(function() {
  messaging.getToken().then(function(refreshedToken) {
    savePushToken(refreshedToken);
  }).catch(function(err) {
    console.log('Unable to retrieve refreshed token ', err);
  });
});
// End Firebase

var cl_cache_expire = 3600 * 24 * 1000 * 30; //courseList and courseCategories cache update after a month.
var forum_url = 'https://groups.google.com/a/nptel.iitm.ac.in/forum/m/#!myforums';
var faq = [{
  'id' : 'gen',
  'name' : 'General',
  'content' :  '<li> <a class="cd-faq-trigger"> A1. What is NPTEL? </a> <div class="cd-faq-content"> <p>NPTEL is an acronym for National Programme on Technology Enhanced Learning which is an initiative by seven Indian Institutes of Technology (IIT Bombay, Delhi, Guwahati, Kanpur, Kharagpur, Madras and Roorkee) and Indian Institute of Science (IISc) for creating course contents in engineering and science. NPTEL provides E-learning through online Web and Video courses in Engineering, Science and Humanities streams.</p> </div> <!-- cd-faq-content --> </li> <li> <a class="cd-faq-trigger" >A2. What is NOC?</a> <div class="cd-faq-content"> <p>NOC stands for NPTEL Online Certification. NPTEL is now offering online certification courses through its portal <a href="https://onlinecourses.nptel.ac.in" target="_blank">https://onlinecourses.nptel.ac.in</a>. There are 4wk, 8wk as well as 12wk courses offered twice a year.</p> </div> <!-- cd-faq-content --> </li> <li> <a class="cd-faq-trigger" >A3. What do I have to do to get a certificate?</a> <div class="cd-faq-content"> <p>If you want to get a certificate from the IITs/IISc after doing the course, you should: - First enroll to the course, which is free - Watch the videos; Submit the weekly Assignments - Register for the in-person proctored certification exam with a nominal fee of Rs 1100 per course - Come write the exam at the designated exam centre - Pass the exam with a consolidated score of 40% or above</p> </div> <!-- cd-faq-content --> </li>'
},
{
  'id' : 'oc',
  'name' : 'Online courses',
  'content': "<li> <a class=\"cd-faq-trigger\" >B1. Where do I get information about up-coming certification courses?<\/a> <div class=\"cd-faq-content\"> <p>Please go to the following link for information on NPTEL online certification courses.<a href=\"http:\/\/nptel.ac.in\/noc\/\" target=\"_blank\">http:\/\/nptel.ac.in\/noc\/<\/a><br>For announcements, you may go to:<a href=\"http:\/\/nptel.ac.in\/\" target=\"_blank\">http:\/\/nptel.ac.in\/<\/a><\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B2. I just came to know that an online course that I wanted to join has concluded its run. Is there any chance of this course being offered again?<\/a> <div class=\"cd-faq-content\"> <p>Depending upon the demand of students and logistics, NPTEL may offer the course again. Kindly keep checking our website for latest news.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B3. How do I enroll\/register for an NPTEL online course?<\/a> <div class=\"cd-faq-content\"> <p>Step 1 - go to the following link - <a href=\"https:\/\/onlinecourses.nptel.ac.in\" target=\"_blank\">https:\/\/onlinecourses.nptel.ac.in<\/a><br>Step 2 \u2013 Click on the tab \"Login\" seen on the top right-hand corner.<br>Step 3 - Use a Google account enabled email id to login.<br>Step 4 \u2013 Choose your desired course. In the upcoming page, go through the details and click on the Join button Next, fill the details and click on the \"Join\" button.<br>Step 5 \u2013 If the course has content uploaded, you will now be able to see it.<br>Once these steps are carried out, you will receive a confirmation e-mail.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B4. Is there a fee to join\/register for an online course?<\/a> <div class=\"cd-faq-content\"> <p> No. Joining\/enrolling for an NPTEL online course is free. Once enrolled, the videos and associated study material may also be downloaded for free. Learning from the course, submitting assignments, participating in the discussion forum is free. <span>To write the final exam, you need to pay Rs. 1100\/- per course.<\/span> <\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B5. What is the eligibility criterion for joining an online course?<\/a> <div class=\"cd-faq-content\"> <p>There is no specific eligibility criterion for any of the NPTEL online courses. The faculty of a particular course may recommend some basic knowledge of certain topics for a person to fully grasp the contents of a course.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B6. How old should I be to register for an online course?<\/a> <div class=\"cd-faq-content\"> <p>Anyone 13 yrs and above may join an online course. <\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B7. Can I join for more than one course at a time?<\/a> <div class=\"cd-faq-content\"> <p>Yes. You may join for any number of courses You can write exams only for a max of 4 courses per semester. <\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B8. I enrolled for a course but now I want to withdraw from this course and join another course. How should I do this?<\/a> <div class=\"cd-faq-content\"> <p>For withdrawing from a course to which you have enrolled, login to the <a href=\"https:\/\/onlinecourses.nptel.ac.in\" target=\"_blank\">https:\/\/onlinecourses.nptel.ac.in<\/a> portal using your email id used to enroll to the course. Click on the email id seen on the right top of the page. You will get a drop down in which there will be an option to unenroll from the course. To join another course, just go to the course you are interested in and click on \"Join\" button.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B9. I have registered for an online course. What is the next step?<\/a> <div class=\"cd-faq-content\"> <p>Those who have registered for a course will receive a confirmation welcome mail. After that, when the course begins and the weekly lessons are released, you will be notified via e-mail. Also, any news, announcements, etc. will be posted in the Announcement Page of the course. You can now start watching the videos. Please keep checking your course page for updates.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B10. It is difficult to watch all the videos online. Can I download notes for these video lectures?<\/a> <div class=\"cd-faq-content\"> <p>Yes. For certain online courses, the text transcription of the video material has been made available for free download at the following link.<span><a href=\" http:\/\/textofvideo.nptel.ac.in\" target=\"_blank\"> http:\/\/textofvideo.nptel.ac.in\/<\/a> > Courses<\/span>. Here, you may search for your desired course and download PDF, MP3 or SRT (subtitle) files. If you do not find your choice of course in that list, please understand that the transcription work is in progress. Kindly bear with us. Some of the text material has also been translated to local languages; do check it out (if available, it will be available within the course page).<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B11. If I were to suggest a particular subject\/topic for an NPTEL online course, will you take that into consideration?<\/a> <div class=\"cd-faq-content\"> <p>We will most definitely take a note of your suggestion and consider that while designing future online certification courses.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B12. How will I come to know about assignments and deadlines?<\/a> <div class=\"cd-faq-content\"> <p>All announcements and other vital information are posted in the Announcement page of the course. Also, e-mail and sms alerts will be sent periodically.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B13. How do I find out my score in each assignment?<\/a> <div class=\"cd-faq-content\"> <p>Your score will be posted online as soon as you submit the assignment. Using your unique password and log in id, you may check your score any time you like.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B14. Will there be self-assessment assignments?<\/a> <div class=\"cd-faq-content\"> <p>Yes. Certain online courses will have these types of assignments. These are meant only for assessing your learning from the course. Typically, these assessments will not carry any marks. The answers for such assignments will also be posted in the course page. Please note that the faculty decides on the type of assignments for each course.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B15. Will the score that I get for the assignment(s) be counted along with my exam marks for the final score?<\/a> <div class=\"cd-faq-content\"> <p>Yes, the assignment scores also contribute to the overall score. 25% of the total score comes from Assignment marks; 75% from final exam.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B16. I may not be able to submit all the assignments. Will this hinder my final score?<\/a> <div class=\"cd-faq-content\"> <p>The final score may be affected as the assignment scores will be counted towards final exam score. But this will not hamper your wirting the certification exam.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B17. What if I have limited internet access? How do I watch videos online?<\/a> <div class=\"cd-faq-content\"> <p>You may download the videos and watch them offline. We have files of smaller formats - flv and 3gp - available on out <a href=\"http:\/\/nptel.ac.in\" target=\"_blank\">http:\/\/nptel.ac.in<\/a> website where the same content will be posted. Also, for certain courses, transcripts are available which are relatively smaller in file size and easier to download. MP3 files (audio) of all online courses are also made available. Please go to the following link to access these files for free. <a href=\"http:\/\/textofvideo.nptel.ac.in\/\" target=\"_blank\">http:\/\/textofvideo.nptel.ac.in\/<\/a><\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B18. How will these online courses fit into my curriculum?<\/a> <div class=\"cd-faq-content\"> <p>You have to check with your college\/Univerisity if they will take this into consideration and incorporate it into your certificate.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B19. I live outside India. Can I still enroll for NPTEL online courses?<\/a> <div class=\"cd-faq-content\"> <p>Yes. You may enroll for any online course no matter where you live and go through the course material.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B20. I live outside India. Can I take the certification exam?<\/a> <div class=\"cd-faq-content\"> <p>NPTEL conducts the final certification exam as a proctored exam where the candidate has to come in person to a designated centre and write the exam. We do not have a process in place to conduct proctored exam for candidates outside India. Hence you can enroll and study using these courses. If you want to take the exam, you have to travel to India and write the exam in one of the designated exam centres.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >B21. Will I get credit equivalents for NPTEL certification courses?<\/a> <div class=\"cd-faq-content\"> <p>You will have to check with the authorities at your college\/university.<\/p> <\/div> <!-- cd-faq-content --> <\/li>"
},
{
  'id':'ce',
  'name':'Certification Examination',
  'content':"<li> <a class=\"cd-faq-trigger\" >C1. What is the exam date for the July to Dec 2018 semester?<\/a> <div class=\"cd-faq-content\"> <p>Oct 7 and Oct 28, 2018 (Sunday - morning & afternoon shifts)<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >C2. How do I register for the online exam?<\/a> <div class=\"cd-faq-content\"> <p>For candidates enrolled to a course, a link will be published for exam registration. Email alerts will be sent to the candidates with the link. Kindly follow the guidelines posted there.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >C3. Since it is an online exam, can I take the exam from home on any day\/date? <\/a> <div class=\"cd-faq-content\"> <p>No. Certification exams will be conducted on 2 Sundays. There will be 2 exam sessions on both days. Morning Session - 9am to 12pm Afternoon session - 2pm to 5pm You will have to appear at the allotted exam centre and produce your Admit Card and Identification Card for verification and take the exam in person. <\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >C4. Due to other commitments, I cannot appear for the exam on the date you had prescribed. Can I take the same exam on another date?<\/a> <div class=\"cd-faq-content\"> <p>At the time of exam registration, you will be choosing exam date and centre. Once this data is submitted, you will not be able to go back and change this input. So if you miss the exam, you cannot take it on another date.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >C5. What is the difference between ONLINE & OFFLINE exam?<\/a> <div class=\"cd-faq-content\"> <p>The exam format - Online or Offline - will be decided by the respective course instructor.<\/p> <p><span>Online exam : (Computer-based exam)<\/span><br> Candidates will have to appear at the allotted exam centre, produce the Hall ticket and Government Identification Card for verification, and take the exam in person. The questions will be on the computer and the answers will have to be entered on the computer. Type of questions may include multiple choice questions, fill in the blanks, short answer type answers, essay type answers, etc.<\/p> <p><span>Offline exam : (Pen-paper exam)<\/span><br> Candidates will have to appear at the allotted exam centre, produce the Hall ticket and Government Identification Card for verification, and take the exam in person. The question paper will be available on the computer. Answer sheets will be given to the candidate. He\/she will have to write the answers on sheets of paper, tie them and submit the same to the invigilator. Type of questions may include multiple choice questions, fill in the blanks, short answer type answers, essay type answers, etc. <\/p> <p><\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >C6. I registered for one online certification exam, but I\u2019ve changed my mind. Now I want to register for another exam on the same day. Can I change it?<\/a> <div class=\"cd-faq-content\"> <p>We suggest that you choose your courses carefully while you register for the exam. If you want to make any changes, you may inform us. If the request for chnage is made within the prescribed timeframe, we will allow the change. Please read the instructions in the exam form carefully.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >C7. Can I register for more than one online exam?<\/a> <div class=\"cd-faq-content\"> <p>Yes. You may participate in 4 online certification exams. Exams are conducted on 2 Sundays. There will be 2 exam sessions on both days. So, you can take two exams per day.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >C8. If I request for any specific city as exam centre that is not already in your list, will you agree to that?<\/a> <div class=\"cd-faq-content\"> <p>Currently, only the centres in the form can be chosen by individuals. If you belong to a college and more than 200 students are appearing for exams on the same date, the college Principal can write to us requesting for a centre in your city and we can try to arrange the same.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >C9. I made on-line payment for the exam. How do I know for sure that the processing was successful and I\'ll get an Admit Card for the exam?<\/a> <div class=\"cd-faq-content\"> <p>If the payment is successful, you will get a confirmation email saying so.<\/p> <\/div> <!-- cd-faq-content --> <\/li>"
},
{
  'id':'dte',
  'name':'During the Exam',
  'content':"<li> <a class=\"cd-faq-trigger\" >D1. Can I use a calculator during the examination?<\/a> <div class=\"cd-faq-content\"> <p>YES. You may carry a scientific calculator.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >D2. What items are not permitted inside the examination venue?<\/a> <div class=\"cd-faq-content\"> <p>Electronic diary, mobile phone, watches, and other electronic gadgets, blank papers, clip boards, log-tables will not be allowed in the examination hall.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <!-- <li> <a class=\"cd-faq-trigger\" >Why does my bank statement show multiple charges for one upgrade?<\/a> <div class=\"cd-faq-content\"> <p>Lorem ipsum dolor sit amet, consectetur adipisicing elit. Blanditiis provident officiis, reprehenderit numquam. Praesentium veritatis eos tenetur magni debitis inventore fugit, magnam, reiciendis, saepe obcaecati ex vero quaerat distinctio velit.<\/p> <\/div> <\/li> --> <li> <a class=\"cd-faq-trigger\" >D3. Am I allowed to leave the examination hall during the test?<\/a> <div class=\"cd-faq-content\"> <p>The exams are scheduled for 3 hours. Candidates are allowed to leave the examination hall after the first 1.5 hours.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >D4. Will I be provided with any rough paper for calculations during the test?<\/a> <div class=\"cd-faq-content\"> <p>Yes. The candidate has to return these papers at the end of the examination.<\/p> <\/div> <!-- cd-faq-content --> <\/li>"
},
{
  'id':'pe',
  'name':'Post-Exam',
  'content':"<li> <a class=\"cd-faq-trigger\" >E1. Will you upload the answers to the questions that we attempted during the online exam(s)? If so, when?<\/a> <div class=\"cd-faq-content\"> <p>Normally the final question paper is not released and hence the solutions also will not be released. If you have any specific doubts, you can write to the course instructor on the discussion forum of the course.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >E2. When will the exam results be published?<\/a> <div class=\"cd-faq-content\"> <p>For an objective online exam, results and the e-certificate (go to the course at nptel.ac.in\/noc) will be available 2-3 weeks after the exam date. For an offline subjective exam (paper and pen), the results and the e-certificate will be made available 5 weeks after the exam.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >E3. I want to contest my exam score. How would I do this?<\/a> <div class=\"cd-faq-content\"> <p>Please write to us explaining the reasons behind your contest. Give us the name of the course, date of exam, roll number and email id.We will forward it to the course instructor and his decision will be implemented.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >E4. When can I expect to receive the hard copy of my certificate?<\/a> <div class=\"cd-faq-content\"> <p>The laminated hard copy of the certificate is usually sent by speed-post 2 to 3 weeks after the exam results are published. An email and sms will be sent to the candidates notifying them about the dispatch.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >E5. Will I receive a certificate showing my exam score?<\/a> <div class=\"cd-faq-content\"> <p>Yes. The score will usually be a combination of assignment and final exam scores, as the course instructor decides.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >E6. I have an up-coming job interview and I need to show the potential employer my certificate. But I have not received the hard copy of my certificate yet. Can you help me out?<\/a> <div class=\"cd-faq-content\"> <p>The e-certificate can be downloaded and printed and used. It is anyway e-verifiable.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >E7. I have shifted my residence to another location recently. Will you please arrange to send the hard copy of my certificate to the new address?<\/a> <div class=\"cd-faq-content\"> <p>At the time of registration of the exam, you will be asked to provide the address where the certificates need to be sent by post. Any request for change in address will not be entertained thereafter. So please give a permanent address while you register for the exam. It cannot be changed once registration is complete.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >E8. There are mistakes in my certificate. How do I get these errors corrected?<\/a> <div class=\"cd-faq-content\"> <p>Within the candidate login, you can log these errors. (<a href=\"http:\/\/nptel.ac.in\/noc\/\" target=\"_blank\">http:\/\/nptel.ac.in\/noc\/<\/a> > Exam Results login) Or, please take a screen-shot of your certificate and send us an e-mail describing the error, within the stipulated time. If the error is genuine and reported to us within the stipulated timeframe, we will send you another re-generated certificate. Else, you have to pay Rs. 200 for a new certificate, with the changes incorporated.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >E9. The certificate I received is damaged. Will you replace it with a good one?<\/a> <div class=\"cd-faq-content\"> <p>Our general policy is that certificates once issued will not be replaced. In special cases, we may consider your request if you send us a screen-shot of the damaged certificate.<\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >E10. What is Candidate log in? I am not able to access candidate log in. Why is that?<\/a> <div class=\"cd-faq-content\"> <p>Only those who have appeared for the NPTEL online exam are referred to as candidates. And only after you are notified by NPTEL about the exam result publication will you be able to access Candidate login.<\/p> <\/div> <!-- cd-faq-content --> <\/li>"
},
{
  'id':'scanc',
  'name':'SWAYAM and NPTEL courses',
  'content':"<li> <a class=\"cd-faq-trigger\" >F1. What is the difference between SWAYAM courses and NPTEL courses?<\/a> <div class=\"cd-faq-content\"><p>SWAYAM is the National MOOCs portal being developed by MHRD, Govt. of India. In order to ensure best quality content is produced and delivered, seven National Coordinators have been appointed under SWAYAM. NPTEL is the official SWAYAM national coordinator for engineering. All NPTEL online certification courses are SWAYAM courses too, and they are available on the SWAYAM platform as well. For certification and examination purposes, we offer the same course on the NPTEL portal. By participating in NPTEL online courses, you and your college are officially participating in SWAYAM.<\/p> <\/div> <!-- cd-faq-content --> <\/li><li> <a class=\"cd-faq-trigger\">F2. Can I enroll & register for exams in SWAYAM portal?<\/a> <div class=\"cd-faq-content\"> <p>You may enroll (join) to courses in SWAYAM portal where you can watch videos and do self-study.<\/p> <p><span>To write exams and get a certificate, you have to:<\/span><br> - enroll at <a href=\"https:\/\/onlinecourses.nptel.ac.in\/\" target=\"_blank\">https:\/\/onlinecourses.nptel.ac.in\/<\/a><br> - register for exams at NPTEL portal<br> - pay exam fees<br> - write exams at designated exam centre<br> - pass the exam by scoring 40 marks or above <\/p> <\/div> <!-- cd-faq-content --> <\/li> <li> <a class=\"cd-faq-trigger\" >F3. If I join to courses in SWAYAM portal, will I get certificate for studying from the video courses?<\/a> <div class=\"cd-faq-content\"> <p>NO. In SWAYAM portal, you can watch videos and do self-study.<\/p> <p><strong>To get a certificate, you need to write the exam.<\/strong><\/p> <p>Please follow these steps:<br>- enroll at <a href=\"https:\/\/onlinecourses.nptel.ac.in\/\" target=\"_blank\">https:\/\/onlinecourses.nptel.ac.in\/<\/a><br> - register for exams at NPTEL portal<br> - pay exam fees<br> - write exams at designated exam centre<br> - pass the exam by scoring 40 marks or above<br> <\/p> <\/div> <!-- cd-faq-content --> <\/li>"
},
{
  'id':'ref',
  'name':'Refunds',
  'content':"<li> <a class=\"cd-faq-trigger\" >G1. After registering for an online exam, I realized that I cannot take the exam on that date. Will you refund my money? If so, how soon should I notify you?<\/a> <div class=\"cd-faq-content\"> <p>Once the exam fee is paid, arrangements will be made for you to take the exam. Please try to take the exam as we will be unable to give a refund in case you cannot.<\/p> <\/div> <\/li> <li> <a class=\"cd-faq-trigger\" >G2. I registered for an online certification exam, but I\u2019ve changed my mind. Now I want to withdraw from this exam. Will you refund my money?<\/a> <div class=\"cd-faq-content\"> <p>Sorry. Once you have registered for an exam, refunds will not be done.<\/p> <\/div> <\/li>"
},
{
  'id':'il',
  'name':'Important Links',
  'content':"<p>E-Mail : <a href=\"mailto:nptel@iitm.ac.in\" target=\"_top\">nptel@iitm.ac.in<\/a><br>NPTEL :&nbsp;<a href=\"http:\/\/nptel.ac.in\/\" target=\"_blank\">http:\/\/nptel.ac.in\/<\/a><br>NPTEL ONLINE COURSE REGISTRATION: <a href=\"https:\/\/onlinecourses.nptel.ac.in\/\" target=\"_blank\">https:\/\/onlinecourses.nptel.ac.in\/<\/a><br>Local Chapter (For Colleges) : <a href=\"http:\/\/nptel.ac.in\/LocalChapter\" target=\"_blank\">http:\/\/nptel.ac.in\/LocalChapter<\/a><br>YOUTUBE : <a href=\"http:\/\/www.youtube.com\/iit\" target=\"_blank\">http:\/\/www.youtube.com\/iit<\/a><br>TEXT OF VIDEOS : <a href=\"http:\/\/textofvideo.nptel.ac.in\/\" target=\"_blank\">http:\/\/textofvideo.nptel.ac.in\/<\/a><\/p>"
}
];
