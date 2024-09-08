//UI logic to render animal data into card elements
let pageOffsetCount = 0; // this is the number (of content elements rendered) to increment with repeated API calls and to send to backend
let totalResultsCount = null; //this is the number of total results returned by API
let currentPage = 1;

const askUserLocation = async () => {
  if (!("geolocation" in navigator)) {
    throw new Error("Geolocation is not supported by this browser.");
  }

  try {
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0,
      });
    });

    const { latitude, longitude } = position.coords;
    return `${latitude},${longitude}`;
  } catch (error) {
    console.error("Error getting user location:", error);
    throw error;
  }
};

//log URL details
function logCurrentUrlDetails() {
  console.debug("Full URL:", window.location.href);
  console.debug("API CALL URL:", window.location.origin + "/data/animals");
  console.debug("Protocol:", window.location.protocol);
  console.debug("Hostname:", window.location.hostname);
  console.debug("Port:", window.location.port);
  console.debug("Pathname:", window.location.pathname);
  console.debug("Search Query:", window.location.search);
  console.debug("Hash:", window.location.hash);
}

const postHiddenForm = async () => {
  //render placeholder skeleton cards
  renderCards([], 9);

  try {
    const hiddenForm = document.getElementById("hidden_form");
    if (hiddenForm) {
      const geolocationInput = document.getElementById("geolocation-input");
      if (!geolocationInput || geolocationInput.value === "") {
        const geolocation = await askUserLocation();
        console.log("Geolocation fetched:", geolocation);

        const data = {
          state: document.getElementById("state_field").value || "",
          country: document.getElementById("country_field").value || "",
          postal_code: document.getElementById("postal_code_field").value || "",
          geolocation: geolocation,
        };
        for (let key in data) {
          const field = document.getElementById(`${key}_field`);

          if (field) field.value = data[key];
        }
        hiddenForm.submit();
      }
    } else {
      console.log("No hidden form found @", window.location.pathname);

      alert("No hidden form found, making API call now");
      return fetchDataAndRender(apiPathName);
    }
  } catch (error) {
    console.error("Error in postHiddenForm:", error);
  }
};

const getImgSrcStr = (species, imgObj) => {
  const defaultAnimalImages = {
    dog: `${window.location.origin}/static/images/graphics/dog_freepik.png`,
    cat: `${window.location.origin}/static/images/graphics/cat_freepik.png`,
    rabbit: `${window.location.origin}/static/images/graphics/easter_bunny_freepik.png`,
    "small-furry": `${window.location.origin}/static/images/graphics/small_furry_freepik.png`,
    horse: `${window.location.origin}/static/images/graphics/horse_freepik.png`,
    bird: `${window.location.origin}/static/images/graphics/bird_eucalyp.png`,
    "scales-fins-other": `${window.location.origin}/static/images/graphics/scales-smashicons.png`,
    barnyard: `${window.location.origin}/static/images/graphics/tracks_freepik.png`,
    misc: `${window.location.origin}/static/images/graphics/pets-iconixar.png`,
  };

  const defaultOutput = defaultAnimalImages[species] || defaultAnimalImages.misc;

  const isValidUrl = (url) => {
    try {
      new URL(url);
      return true;
    } catch (error) {
      return false;
    }
  };

  const findValidImageUrl = (obj) => {
    if (typeof obj === 'string') {
      return isValidUrl(obj) ? obj : null;
    }
    if (Array.isArray(obj)) {
      for (const item of obj) {
        const result = findValidImageUrl(item);
        if (result) return result;
      }
    }
    if (typeof obj === 'object' && obj !== null) {
      const sizeKeys = ["full", "large", "xxl", "medium", "small"];
      for (const key of sizeKeys) {
        if (obj[key]) {
          const result = findValidImageUrl(obj[key]);
          if (result) return result;
        }
      }
      for (const value of Object.values(obj)) {
        const result = findValidImageUrl(value);
        if (result) return result;
      }
    }
    return null;
  };

  if (!imgObj) return defaultOutput;

  const validImageUrl = findValidImageUrl(imgObj);
  return validImageUrl || defaultOutput;
};

// Function to create card elements
function createCardElementFromData(animal) {
  const colDiv = document.createElement("div");
  colDiv.className = "col";

  const cardDiv = document.createElement("div");
  cardDiv.className = "card text-start h-100";

  if (animal.photos && animal.photos.length > 0) {
    const img = document.createElement("img");
    img.src = getImgSrcStr(animal?.type, animal.photos);
    img.className = "card-img-top";
    img.alt = `${animal.name}-photo`;
    cardDiv.appendChild(img);
  }

  const cardBody = document.createElement("div");
  cardBody.className = "card-body";

  const cardTitle = document.createElement("h4");
  cardTitle.id = "result-name";
  cardTitle.className = "card-title";
  cardTitle.textContent = animal.name;
  cardBody.appendChild(cardTitle);

  const cardText = document.createElement("div");
  cardText.id = `${animal.name}-type-size-age`;
  cardText.className = "card-text";

  // Add animal type emoji or question mark
  if (animal.type) {
    const typeEmoji = animal_emojis[animal.type.toLowerCase()] || "❓";
    cardText.appendChild(document.createTextNode(typeEmoji + " "));
  }

  // Add breed information
  if (animal.breeds) {
    const breedBadge = document.createElement("span");
    breedBadge.className = "badge rounded-pill bg-primary";
    breedBadge.textContent = animal.breeds.unknown
      ? "Unknown Breed"
      : animal.breeds.mixed
      ? `${animal.breeds.primary}/${animal.breeds.secondary}`
      : animal.breeds.primary;
    cardText.appendChild(breedBadge);
  }

  // Add size, age, gender badges
  ["size", "age", "gender"].forEach((attr) => {
    if (animal[attr]) {
      const badge = document.createElement("span");
      badge.className = `badge rounded-pill bg-${
        attr === "size"
          ? "info"
          : attr === "age"
          ? "warning"
          : animal.gender === "Female"
          ? "light text-dark"
          : "primary text-dark"
      }`;
      badge.textContent = animal[attr];
      cardText.appendChild(badge);
    }
  });

  // Add attributes badges
  if (animal.attributes) {
    const { spayed_neutered, house_trained, declawed, special_needs, shots_current } = animal.attributes;

    if (spayed_neutered) {
      const spayedBadge = document.createElement("span");
      spayedBadge.className = "badge rounded-pill bg-success";
      spayedBadge.textContent = "Spayed/Neutered";
      cardText.appendChild(spayedBadge);
    }

    if (house_trained) {
      const houseTrainedBadge = document.createElement("span");
      houseTrainedBadge.className = "badge rounded-pill bg-success";
      houseTrainedBadge.textContent = "House Trained";
      cardText.appendChild(houseTrainedBadge);
    }

    if (declawed) {
      const declawedBadge = document.createElement("span");
      declawedBadge.className = "badge rounded-pill bg-danger";
      declawedBadge.textContent = "Declawed";
      cardText.appendChild(declawedBadge);
    }

    if (special_needs) {
      const specialNeedsBadge = document.createElement("span");
      specialNeedsBadge.className = "badge rounded-pill bg-danger";
      specialNeedsBadge.textContent = "Special Needs";
      cardText.appendChild(specialNeedsBadge);
    }

    if (shots_current) {
      const shotsCurrentBadge = document.createElement("span");
      shotsCurrentBadge.className = "badge rounded-pill bg-success";
      shotsCurrentBadge.textContent = "Vaccinated";
      cardText.appendChild(shotsCurrentBadge);
    }
  }

  cardBody.appendChild(cardText);

  // Add location
  const locationDiv = document.createElement("div");
  locationDiv.className = `${animal.name}-location mt-2`;
  locationDiv.innerHTML = `<i class="fa fa-map-marker-alt text-danger"></i> <span>${animal.contact.address.city}, ${animal.contact.address.state}, ${animal.contact.address.country}</span>`;
  cardBody.appendChild(locationDiv);

  cardBody.appendChild(document.createElement("hr"));

  // Add description
  if (animal.description) {
    const descriptionP = document.createElement("p");
    descriptionP.textContent = animal.description;
    cardBody.appendChild(descriptionP);
  }

  // Add tags
  animal.tags.forEach((tag) => {
    const tagBadge = document.createElement("span");
    tagBadge.className = "badge rounded-pill bg-success";
    tagBadge.textContent = tag;
    cardBody.appendChild(tagBadge);
  });

  // Add adoptable status
  if (animal.status === "adoptable") {
    const alertDiv = document.createElement("div");
    alertDiv.className = "alert alert-success mt-2 justify-content-center";
    alertDiv.role = "alert";

    const adoptLink = document.createElement("a");
    adoptLink.href = animal.url;
    adoptLink.className = "btn btn-info";
    adoptLink.textContent = "Adopt me!";
    alertDiv.appendChild(adoptLink);

    const followLink = document.createElement("a");
    followLink.href = animal.url;
    followLink.className = "btn btn-info";
    followLink.textContent = "Follow";
    alertDiv.appendChild(followLink);

    cardBody.appendChild(alertDiv);
  }

  cardDiv.appendChild(cardBody);
  colDiv.appendChild(cardDiv);

  return colDiv;
}


// UI UTIL FUNCTIONS //////////////////////////////////////////////////////////////////////////////////////////

const animal_emojis = {
  dog: "🐶",
  cat: "🐱",
  rabbit: "🐰",
  "small-furry": "🐹",
  horse: "🐴",
  bird: "🐦",
  "scales-fins-other": "🦎",
  barnyard: "🐄",
};

const clearContainer = (containerId = "animal-results-cards-container") => {
  const container = document.getElementById(containerId);
  if (container && container.hasChildNodes()) {
    container.innerHTML = ""; // Clear all child elements
    while (container.childElementCount > 0) {
      let lastChild = container.lastElementChild;
      container.removeChild(lastChild);
    }
  } else {
    console.error(`Container with ID "${containerId}" not found.`);
  }
};

const defaultBreakpoints = {
  mobile: 1, // 1 column for mobile
  tablet: 3, // 3 columns for tablet
  desktop: 9, // 9 columns for desktop
};

function getColumnCount(breakpoints = defaultBreakpoints) {
  const width = window.innerWidth;

  if (width < 576) {
    return breakpoints.mobile; // Mobile
  } else if (width >= 576 && width < 768) {
    return breakpoints.tablet; // Tablet
  } else {
    return breakpoints.desktop; // Desktop
  }
}

function updateRenderedDiff() {
  const rowDiv = document.getElementById("animal-results-cards-container");
  const columnCount = getColumnCount();
  const renderedDiff = rowDiv.childElementCount % columnCount;

  if (renderedDiff !== 0) {
    console.log(`renderedDiff = ${renderedDiff}, generating skeleton cards`);
    generateSkeletonCards(renderedDiff);
  }
}

// UI UTIL FUNCTIONS //////////////////////////////////////////////////////////////////////////////////////////

const generateSkeletonCards = (skeletonCount = 9) => {
  const resultsContainerID = "animal-results-cards-container";
  const resultsContainer = document.getElementById(resultsContainerID);
  // Create skeleton cards
  for (let i = 0; i < skeletonCount; i++) {
    const skeletonCard = createSkeletonCard();
    resultsContainer.append(skeletonCard);

    //increment page offset count
    pageOffsetCount += i;
  }
  //logic to ensure pageOffsetCount is accurate

  pageOffsetCount =
    pageOffsetCount === resultsContainer.childElementCount
      ? pageOffsetCount
      : resultsContainer.childElementCount;
};

// Function to clear skeleton cards
const clearSkeletonCards = () => {
  const rowDiv = document.getElementById("animal-results-cards-container");
  // Filter out skeleton cards
  Array.from(rowDiv.children).forEach((child) => {
    if (child.className.includes("skeleton-card")) {
      rowDiv.removeChild(child);
    }
  });
};

// Function to render cards
const renderCards = (animals = []) => {
  const rowDivID = "animal-results-cards-container";
  const rowDiv = document.getElementById(rowDivID);

  // Remove skeleton cards before rendering actual data
  clearSkeletonCards();

  // Check if there are animals to render
  if (animals.length > 0) {
    animals.forEach((animal) => {
      const cardElement = createCardElementFromData(animal);
      rowDiv.appendChild(cardElement);
    });
    console.info(`Cards rendered, offset count updated to: ${pageOffsetCount}`);
  } else {
    flashMessage("No animals to render.", false);
    //reset pageOffsetCount if incremented to num of children in rowDiv
    pageOffsetCount =
      pageOffsetCount === rowDiv.childElementCount
        ? pageOffsetCount
        : rowDiv.childElementCount;
  }
};

function createSkeletonCard() {
  const resultsContainer = document.getElementById(
    "animal-results-cards-container"
  );
  const colDiv = document.createElement("div");
  colDiv.className = "col-lg-4 mb-4 mb-lg-0";
  colDiv.id = `skeleton-card-${resultsContainer.childElementCount + 1}`;

  const cardDiv = document.createElement("div");
  cardDiv.className = "card text-start skeleton-card";

  const skeletonImg = document.createElement("div");
  skeletonImg.className = "skeleton-img shimmer";
  cardDiv.appendChild(skeletonImg);

  const cardBody = document.createElement("div");
  cardBody.className = "card-body";

  const skeletonTitle = document.createElement("div");
  skeletonTitle.className = "skeleton-title shimmer";
  cardBody.appendChild(skeletonTitle);

  const skeletonText = document.createElement("div");
  skeletonText.className = "skeleton-text shimmer";
  cardBody.appendChild(skeletonText);

  const skeletonBadges = document.createElement("div");
  skeletonBadges.className = "skeleton-badges";
  for (let i = 0; i < 3; i++) {
    const badge = document.createElement("div");
    badge.className = "skeleton-badge shimmer";
    skeletonBadges.appendChild(badge);
  }
  cardBody.appendChild(skeletonBadges);

  cardDiv.appendChild(cardBody);
  colDiv.appendChild(cardDiv);

  return colDiv;
}

const flashMessage = (message, success = false) => {
  const errorContainer = document.getElementById(
    "flash_message_container" //"animal-results-error-container"
  );
  // Create a div element for the error message
  const errorDiv = document.createElement("div");
  errorDiv.textContent = message;
  errorDiv.style.position = "fixed";
  errorDiv.style.top = "40px";
  errorDiv.style.right = "20px";
  errorDiv.style.padding = "10px";
  errorDiv.style.backgroundColor = success ? "green" : "#red"; // Red background for error // Green for success
  errorDiv.style.color = "white";
  errorDiv.style.borderRadius = "5px";
  errorDiv.style.zIndex = "1000";
  errorDiv.style.opacity = "0";
  errorDiv.style.transition = "opacity 0.5s";

  // Append the error message to the body
  errorContainer.appendChild(errorDiv);

  // Show the error message
  setTimeout(() => {
    errorDiv.style.opacity = "1";
  }, 100000);

  // Hide the error message after 3 seconds
  setTimeout(() => {
    errorDiv.style.opacity = "0";
    // Remove the error message from the DOM after fading out
    setTimeout(() => {
      errorDiv.remove();
    }, 500);
  }, 50000);

  console.debug(`${success ? "Success" : "Error"} flash message => ${message}`);
};

const fetchDataAndRender = (apiURL) => {
  fetch(apiURL)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.results && data.results.length > 0) {
        flashMessage(
          `Results fetched! ${data.results.length} animals found.`,
          true
        );
        renderCards(data.results);

        // Update totalResultsCount and currentPage
        totalResultsCount = data.pagination.total_count;
        currentPage = data.pagination.current_page;

        console.log(
          `Total results = ${totalResultsCount}; current page = ${currentPage}`
        );
      } else {
        flashMessage("No results found.", false);
      }
    })
    .catch((error) => {
      console.error("Error fetching data:", error);
      flashMessage(`Error fetching data: ${error}`, false);
    });
};

// Call this function to log the URL details
logCurrentUrlDetails();
// Render skeleton cards on page load
// renderCards([], 9);
// Fetch animals data from API and render cards
let apiURLString = window.location.origin + "/data/animals";
console.log(`apiURLString = ${apiURLString}`);

document.addEventListener("DOMContentLoaded", async () => {
  generateSkeletonCards(20);
  fetchDataAndRender(apiURLString);
});

// window.addEventListener("resize", () => {
//   updateRenderedDiff();
//   console.log("breakpoints adjusted");
// });
