'''Written by Cael Shoop.'''

from discord import Member


class Player:
    def __init__(self, member: Member):
        self.name = member.name
        self.member = member

    def to_dict() -> dict:
        data = {}
        return data

    @classmethod
    def from_dict(cls):
        return cls()
