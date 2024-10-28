// Word banks
const rescueVerbs = ["Foster", "Adopt", "Volunteer", "Find", "Browse", "Save"];
const callToActionPhrases = [
  "Are you an animal lover?",
  "Do you want to help animals in need?",
  "Are you looking for a friend to adopt?",
  "Do you want to volunteer?",
  "Do you interested in being an animal foster?",
  "Are you looking to support your local rescues?",
  "SIGN UP with Far Fetched today!",
];
const rescueSubjects = ['Furry Friends', "Rescue Animals In Need", "Local Animal Rescues", "Animal Shelters Near You"]

// Element IDs
const SubjectTextQueryClassTag = "animated-subject-text"; //animate rescueSubjects
const actionTextQueryClassTag = "animated-action-text"; //animate rescue verbs
const callToActionQueryClassTag = "animated-cta-text"; //animal CTA phrases

// Update function
const updateText = (QueryClassTag, wordBank, interval = 1500) => {
  /**
   * Update UI text in <element class=QueryClassTag> with wordBank strings at set intervals
   * @param {string} QueryClassTag - ID of HTML element to update
   * @param {array} wordBank - Array of string values to update the text with
   * @param {number} interval - Time interval in milliseconds for updating
   */

  const changeText = (QueryClassTag, newText) => {
    const element = document.querySelector(QueryClassTag);
    element.textContent = newText;
  };

  wordBank.forEach((phrase, index) => {
    setTimeout(() => {
      changeText(QueryClassTag, phrase);
    }, interval * index);
  });
};

// Run update functions on page load
window.addEventListener("load", () => {
  console.log("HOME DOM ELEMENTS LOADED");
  updateText(SubjectTextQueryClassTag, rescueSubjects);
  updateText(actionTextQueryClassTag, rescueVerbs);
  updateText(callToActionQueryClassTag, callToActionPhrases);
});
