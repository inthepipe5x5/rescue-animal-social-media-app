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
// Function to create card elements
function createCardElementFromData(animal) {
  const colDiv = document.createElement("div");
  colDiv.className = "col";

  const cardDiv = document.createElement("div");
  cardDiv.className = "card text-start h-100";

  if (animal.photos && animal.photos.length > 0) {
    const img = document.createElement("img");
    img.src = animal.photos[0].full;
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

  // Add size, age, gender, and special needs badges
  ["size", "age", "gender", "attributes"].forEach((attr) => {
    if (animal[attr]) {
      const badge = document.createElement("span");
      badge.className = `badge rounded-pill bg-${
        attr === "size"
          ? "info"
          : attr === "age"
          ? "warning"
          : attr === "gender"
          ? animal.gender === "Female"
            ? "light text-dark"
            : "primary text-dark"
          : "danger"
      }`;
      badge.textContent = animal[attr];
      if (attr === "gender")
        badge.textContent +=
          animal.gender === "Female"
            ? "💅✨"
            : animal.gender === "Male"
            ? "🤠"
            : "👩🏼‍🤝‍🧑🏼";
      if (attr === "attributes" && animal.attributes.special_needs)
        badge.textContent = "♿";
      cardText.appendChild(badge);
    }
  });

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
    resultsContainer.appendChild(skeletonCard);

    //increment page offset count
    pageOffsetCount += i;
  }
  //logic to ensure pageOffsetCount is accurate

  pageOffsetCount =
    pageOffsetCount === resultsContainer.childElementCount
      ? pageOffsetCount
      : resultsContainer.childElementCount;
};

// Function to render cards
const renderCards = (animals = []) => {
  const rowDivID = "animal-results-cards-container";
  const rowDiv = document.getElementById("animal-results-cards-container");
  clearContainer(rowDivID);

  //generate skeleton cards to create loading effect only if row.Div childElementCount === 0

  if (!animals && rowDiv.childElementCount === 0) {
    generateSkeletonCards(20);
  }

  //render cards
  if (animals.length > 0) {
    animals.forEach((animal) => {
      const cardElement = createCardElementFromData(animal);
      // Filter skeleton cards
      let ArrOfSkeletonCardToRemove = Array.from(rowDiv.children).filter(
        (childNode) => childNode.className.includes("skeleton")
      );
      let firstSkeletonCard = ArrOfSkeletonCardToRemove[0];
      if (firstSkeletonCard) {
        rowDiv.replaceChild(cardElement, firstSkeletonCard);
        pageOffsetCount += i;
      }
      //increment page offset count
    });
    console.info(`Cards rendered, offset count updated to: ${pageOffsetCount}`);
  } else {
    //handle errors
    flashMessage(
      `Error, animals length === ${animals.length}, pageOffsetCount = ${pageOffsetCount}`,
      false
    );
    //reset pageOffsetCount if incremented to num of children in rowDiv
    pageOffsetCount =
      pageOffsetCount === rowDiv.childElementCount
        ? pageOffsetCount
        : rowDiv.childElementCount;
    return; //do nothing if no animals passed in
  }

  // container.appendChild(rowDiv);
};

function createSkeletonCard() {
  const resultsContainer = document.getElementById(
    "animal-results-cards-container"
  );
  const colDiv = document.createElement("div");
  colDiv.className = "col-lg-4 mb-4 mb-lg-0";
  colDiv.id = `skeleton-card-${resultsContainer.childElementCount + 1}`;

  const cardDiv = document.createElement("div");
  cardDiv.className = "card text-start h-100 skeleton-card";

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
    "flash_message_container"//"animal-results-error-container"
  );
  // Create a div element for the error message
  const errorDiv = document.createElement("div");
  errorDiv.textContent = message;
  errorDiv.style.position = "fixed";
  errorDiv.style.top = "20px";
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
  }, 1000);

  // Hide the error message after 3 seconds
  setTimeout(() => {
    errorDiv.style.opacity = "0";
    // Remove the error message from the DOM after fading out
    setTimeout(() => {
      errorDiv.remove();
    }, 500);
  }, 5000);

  console.debug(`${success ? "Success" : "Error"} flash message => ${message}`)
};

const fetchDataAndRender = (apiURL) => {
  fetch(apiURL)
    .then((response) => {
      // Check if the response is ok (status in the range 200-299)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json(); // Return the parsed JSON directly
    })
    .then((data) => {
      flashMessage(
        `Results fetched! ${window.location.pathname.split("/")[1]} found: ${
          data?.results?.length || 0
        }`,
        true
      );
      console.log(`Fetched data: ${logCurrentUrlDetails()}`, {
        results: data["results"]?.length,
        ...data,
      });

      // Clear the container before rendering new cards
      // clearContainer(); //commented out to try the other way instead

      if (data.results && data.results.length > 0) {
        renderCards(data?.results);
        //set totalResultsCount
        totalResultsCount = data?.pagination?.total_count;
        currentPage = data?.pagination?.current_page;
        console.log(
          `total results = ${totalResultsCount}; current page = ${currentPage}`
        );

        updateRenderedDiff();
      }
    })
    .catch((error) => {
      console.error("Error fetching data:", error, logCurrentUrlDetails());
      flashMessage(`Error fetching data: ${error}`, false);
    });
};

// Call this function to log the URL details
logCurrentUrlDetails();
// Render skeleton cards on page load
// renderCards([], 9);
// Fetch animals data from API and render cards
let apiURLString = window.location.origin + "/data/animals";
console.log(apiURLString);

document.addEventListener("DOMContentLoaded", async () => {
  generateSkeletonCards(20);
  fetchDataAndRender(apiURLString);
});

// Call the function initially to set the correct renderedDiff
updateRenderedDiff();

window.addEventListener("resize", () => {
  updateRenderedDiff();
  console.log("breakpoints adjusted");
});
