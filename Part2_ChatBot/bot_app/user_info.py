from pydantic import BaseModel

class UserInfo(BaseModel):
    first_name: str
    last_name: str
    id_number: str
    gender: str
    age: int
    hmo: str         # "מכבי", "מאוחדת", "כללית"
    hmo_card: str
    tier: str        # "זהב", "כסף", "ארד"
