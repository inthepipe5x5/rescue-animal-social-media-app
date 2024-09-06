//front-end logic to grab user geolocation
//run on page load
const postLocationData = async (endpoint, params) => {
  const { state, postal_code, country, geolocation } = params || null;

  const API_URL = "localhost/" + endpoint;
  try {
    const response = await fetch(API_URL, {
      body: JSON.stringify({
        location: {
          state,
          country,
          postal_code,
          geolocation,
        },
      }),
    });

    return response;
  } catch (error) {
    console.error(`Error posting location data to API => ${error}`);
  }
};
const getUserLocation = async () => {
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
