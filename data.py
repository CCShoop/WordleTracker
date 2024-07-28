'''Written by Cael Shoop.'''

from random import randint
from datetime import datetime, timedelta


class TrackerData:
    def __init__(self,
                 gameNumber: int,
                 savedLettersCount: int,
                 letter: chr,
                 savedLetters: list,
                 scored: bool):
        self.gameNumber = gameNumber
        self.SAVED_LETTERS_COUNT = savedLettersCount
        self.letter = letter
        self.savedLetters = savedLetters
        self.scored = scored

    def get_new_letter(self) -> None:
        letter = chr(randint(ord('A'), ord('Z')))
        while letter in self.savedLetters:
            letter = chr(randint(ord('A'), ord('Z')))
        if len(self.savedLetters) >= self.SAVED_LETTERS_COUNT:
            self.savedLetters.remove(self.savedLetters[0])

    def reset(self) -> None:
        self.get_new_letter()
        self.gameNumber += 1
        self.scored = False

    def to_dict(self) -> dict:
        payload = {}
        payload["gameNumber"] = self.gameNumber
        payload["savedLettersCount"] = self.SAVED_LETTERS_COUNT
        payload["letter"] = self.letter
        payload["savedLetters"] = self.savedLetters
        payload["scored"] = self.scored
        return payload

    @classmethod
    def from_dict(cls, payload: dict):
        return cls(gameNumber=payload["gameNumber"],
                   savedLettersCount=payload["savedLettersCount"],
                   letter=payload["letter"],
                   savedLetters=payload["savedLetters"],
                   scored=payload["scored"]
                   )

class PlayerData:
    def __init__(self,
                 submitted: bool,
                 guesses: int,
                 imagePath: str,
                 msgContent: str,
                 resetTime: datetime,
                 warningSent: bool):
        self.submitted = submitted
        self.guesses = guesses
        self.imagePath = imagePath
        self.msgContent = msgContent
        self.resetTime = resetTime
        self.warningSent = warningSent

    def reset(self) -> None:
        self.submitted = False
        self.guesses = 0
        self.imagePath = ''
        self.msgContent = ''
        self.resetTime += timedelta(days=1)
        self.warningSent = False

    def to_dict(self) -> dict:
        payload = {}
        payload["submitted"] = self.submitted
        payload["guesses"] = self.guesses
        payload["imagePath"] = self.imagePath
        payload["msgContent"] = self.msgContent
        payload["resetTime"] = self.resetTime.isoformat()
        payload["warningSent"] = self.warningSent
        return payload

    @classmethod
    def from_dict(cls, payload: dict):
        return cls(submitted=payload["submitted"],
                   guesses=payload["guesses"],
                   imagePath=payload["imagePath"],
                   msgContent=payload["msgContent"],
                   resetTime=datetime.fromisoformat(payload["resetTime"]),
                   warningSent=payload["warningSent"]
                   )
