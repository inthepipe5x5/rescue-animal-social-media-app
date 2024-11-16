from typing import TypeAlias, TypedDict, Optional, Union, List, Tuple
import datetime
from enum import Enum
from pandas import DataFrame




class AnimalType(Enum):
    # The class `AnimalType` defines an enumeration of different types of animals.
    DOG = "dog"
    CAT = "cat"
    RABBIT = "rabbit"
    SMALL_FURRY = "small-furry"
    HORSE = "horse"
    BIRD = "bird"
    SCALES_FINS_OTHER = "scales-fins-other"
    BARNYARD = "barnyard"


class FormattedAnimalType(Enum):
    # The class `AnimalType` defines an enumeration of different types of animals.
    # animal types returned from the PetFinder API and the required format for animal_type params
    DOG = "Dog"
    CAT = "Cat"
    RABBIT = "Rabbit"
    SMALL_FURRY = "Small & Furry"
    HORSE = "Horse"
    BIRD = "Bird"
    SCALES_FINS_OTHER = "Scales, Fins & Other"
    BARNYARD = "Barnyard"


# Types from PetPy lib
# Parameter Types
AnimalTypes: TypeAlias = Union[str, List[Union[str]], tuple, AnimalType]
PetfinderID: TypeAlias = Union[int, str, List[Union[int, str]], Tuple[Union[int, str]]]
AnimalFeatures: TypeAlias = Union[
    bool, str, List[str], tuple[str, ...]
]  # accepts a list/tuple of features, which are either boolean or string
Date: TypeAlias = Union[str, datetime.datetime]


# Return Types
RequestedContent: TypeAlias = Union[list[dict], dict, DataFrame]
Animals: TypeAlias = Union[list[dict], dict, DataFrame]


class AnimalReqParams(TypedDict, total=False):
    """Typing for req params being made to PetFinder API

    # Usage
    animals_request_params: AnimalReqParams = {
        "animal_type": "dog",
        "breed": ["Labrador", "Golden Retriever"],
        "size": "large",
        "good_with_children": True,
        "results_per_page": 20
    }

    """

    name: Optional[str]
    animal_id: Optional[PetfinderID]
    animal_type: Optional[Union[str, FormattedAnimalType]]
    status: Optional[str]

    age: Optional[AnimalFeatures]
    gender: Optional[AnimalFeatures]
    breed: Optional[AnimalFeatures]
    size: Optional[AnimalFeatures]
    color: Optional[AnimalFeatures]
    coat: Optional[AnimalFeatures]

    # env
    children: Optional[bool]
    dogs: Optional[bool]
    cats: Optional[bool]

    # attributes
    declawed: Optional[bool]
    house_trained: Optional[bool]
    special_needs: Optional[bool]

    #lazy import to prevent circular import
    from Project.core.types import UserLocationData
    
    # meta
    before_date: Optional[Date]
    after_date: Optional[Date]
    results_per_page: Optional[int]
    page: Optional[int]
    organization_id: Optional[PetfinderID]
    location: Optional[UserLocationData]
    distance: Optional[int]
    query: Optional[str]
    sort: Optional[str]
