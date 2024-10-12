
// UI UTIL FUNCTIONS //////////////////////////////////////////////////////////////////////////////////////////

const generateSkeletonCards = (skeletonCount = 10) => {
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
        //REMOVE LATER
        console.debug(animal?.name, animal?.photos)
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