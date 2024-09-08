// Word banks
const rescueVerbs = ["Foster", "Adopt", "Volunteer", "Find"];
const callToActionPhrases = [
  "Are you an animal lover?",
  "Do you want to help animals in need?",
  "Are you looking for a friend to adopt?",
  "Do you want to volunteer?",
  "Do you interested in being an animal foster?",
  "Are you looking to support your local rescues?",
  "SIGN UP with Far Fetched today!",
];

// Element IDs
const actionTextElementID = "hero-action-text";
const callToActionElementID = "call-to-action-text";

// Update function
const updateText = (elementID, wordBank, interval = 1500) => {
  /**
   * Update UI text in <element id=elementID> with wordBank strings at set intervals
   * @param {string} elementID - ID of HTML element to update
   * @param {array} wordBank - Array of string values to update the text with
   * @param {number} interval - Time interval in milliseconds for updating
   */

  const changeText = (elementID, newText) => {
    const element = document.getElementById(elementID);
    element.textContent = newText;
  };

  wordBank.forEach((phrase, index) => {
    setTimeout(() => {
      changeText(elementID, phrase);
    }, interval * index);
  });
};

// Run update functions on page load
window.addEventListener("load", () => {
  console.log("HOME DOM ELEMENTS LOADED");
  updateText(actionTextElementID, rescueVerbs);
  updateText(callToActionElementID, callToActionPhrases);
});
