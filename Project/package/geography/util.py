""" Utility class and methods for handling geography and location dat
"""

import pycountry


class GeoUtil:

    def lookup_country(search_string) -> list:

        return [
            dict(country_obj)
            for country_obj in pycountry.countries.search_fuzzy(search_string)
        ]
