//UI logic to render animal data into card elements

//log URL details
function logCurrentUrlDetails() {
  console.debug("Full URL:", window.location.href);
  console.debug("Protocol:", window.location.protocol);
  console.debug("Hostname:", window.location.hostname);
  console.debug("Port:", window.location.port);
  console.debug("Pathname:", window.location.pathname);
  console.debug("Search Query:", window.location.search);
  console.debug("Hash:", window.location.hash);
}

const postHiddenForm = async () => {
  try {
    const hiddenForm = document.getElementById("hidden_form");
    if (hiddenForm) {
      const geolocationInput = document.getElementById("geolocation-input");
      if (!geolocationInput || geolocationInput.value === "") {
        const geolocation = await getUserLocation();
        console.log("Geolocation fetched:", geolocation);

        const data = {
          // state: document.getElementById("state_field").value || "",
          // country: document.getElementById("country_field").value || "",
          // postal_code: document.getElementById("postal_code_field").value || "",
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
      const apiPathName = window.location.origin + "/data/animals";
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
    const typeEmoji = animal_emojis[animal.type.toUpperCase()] || "❓";
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

// Function to render cards
function renderCards(animals = [], skeletonCount = 8) {
  const container = document.getElementById("animal-results-cards-container");
  container.innerHTML = ""; // Clear existing content

  const rowDiv = document.createElement("div");
  rowDiv.className = "row row-cols-3 row-cols-md-3 g-4";

  if (!animals || animals.length === 0) {
    // Create skeleton cards
    for (let i = 0; i < skeletonCount; i++) {
      const skeletonCard = createSkeletonCard();
      rowDiv.appendChild(skeletonCard);
    }
  } else {
    animals.forEach((animal) => {
      const cardElement = createCardElement(animal);
      rowDiv.appendChild(cardElement);
    });
  }

  container.appendChild(rowDiv);
}

function createSkeletonCard() {
  const colDiv = document.createElement("div");
  colDiv.className = "col";

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

// Fetch data from API and render cards
function fetchDataAndRender(apiURL) {
  fetch(apiURL)
    .then((response) => response.json())
    .then((data) => {
      if (data.results && data.results.animals.length > 0) {
        renderCards(data.results.animals);
      }
    })
    .catch((error) =>
      console.error("Error fetching data:", error, logCurrentUrlDetails())
    );
}

