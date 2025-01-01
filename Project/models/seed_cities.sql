INSERT INTO
  public.cities (
    id,
    "wikiDataId",
    type,
    name,
    country_name,
    country_code,
    region_name,
    region_code,
    elevation_meters,
    geolocation,
    population,
    timezone,
    provider
  )
VALUES
  (
    '123214',
    'Q60',
    'CITY',
    'New York City',
    'United States of America',
    'US',
    'New York',
    'NY',
    10,
    '40.7,-74',
    8804190,
    'America__New_York',
    'geodb_cities'
  ),
  (
    '10908',
    'Q172',
    'CITY',
    'Toronto',
    'Canada',
    'CA',
    'Ontario',
    'ON',
    76,
    '43.670,-79.387',
    2794356,
    'America__Toronto',
    'geodb_cities'
  ),
  (
    '3850170',
    'Q65',
    'CITY',
    'Los Angeles',
    'United States of America',
    'US',
    'California',
    'CA',
    106,
    '34.052,-118.243',
    3898747,
    'America__Los_Angeles',
    'geodb_cities'
  )

-- Los Angelos data 
-- {"data":{"id":3850170,"wikiDataId":"Q65","type":"CITY","city":"Los Angeles","name":"Los Angeles","country":"United States of America","countryCode":"US","region":"California","regionCode":"CA","regionWdId":"Q99","elevationMeters":106,"latitude":34.05223,"longitude":-118.24368,"population":3898747,"timezone":"America__Los_Angeles","deleted":false}}
