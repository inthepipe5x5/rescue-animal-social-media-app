//word banks
const rescueVerbsForHomeHeroBannerActionText = ["Foster", "Adopt", "Volunteer", "Find"];
const callToActionPhrases = [
  "Are you an animal lover?",
  "Do you want to help animals in need?",
  "Are you looking for a friend to adopt?",
  "Do you want to volunteer?",
  "Do you interested in being an animal foster?",
  "Are you looking to support your local rescues?",
  "SIGN UP with Far Fetched today!",
];

//elements
const homeHeroBannerActionText = "hero-banner-text-action";

const homeHeroCallToActionPElement = "call-to-action-carousel-text";

//update function

const updatePhrases = (elementID, wordBank, interval = 1500) => {
  /*
    function to update UI text
    params: 
    - elementID - id of HTML element to update
    - workBank - array of values to update the text of element with
    - interval - time interval in MS to update by
    */

  const changeText = (elementID, newText) => {
    const elementToBeUpdated = document.getElementById(elementID);
    elementToBeUpdated.textContent = newText;
  };

  for (let phrase in wordBank) {
    setTimeout(() => {
      changeText(elementID, phrase);
    }, interval);
  }
};

//run update elements functions on page load
document
  .getElementById(homeHeroBannerActionText)
  .addEventListener(
    "load",
    updatePhrases(
      homeHeroBannerActionText,
      rescueVerbsForHomeHeroBannerActionText
    )
  );
document
  .getElementById(homeHeroCallToActionPElement)
  .addEventListener(
    "load",
    updatePhrases(homeHeroCallToActionPElement, callToActionPhrases)
  );
