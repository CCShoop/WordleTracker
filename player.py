'''Written by Cael Shoop.'''

from discord import Member, Guild

from data import PlayerData

class Player:
    def __init__(self,
                 member: Member,
                 registered: bool,
                 prevData: PlayerData,
                 data: PlayerData):
        self.name = member.name
        self.member = member
        self.registered = registered
        self.prevData = prevData
        self.data = data

    def to_dict(self) -> dict:
        payload = {}
        payload["memberId"] = self.member.id
        payload["registered"] = self.registered
        payload["prevData"] = self.prevData.to_dict()
        payload["data"] = self.data.to_dict()
        return payload

    @classmethod
    def from_member(cls, member: Member):
        return cls(member=member,
                   registered=True,
                   prevData=None,
                   data=PlayerData()
                   )

    @classmethod
    def from_dict(cls, guild: Guild, payload: dict):
        member = guild.get_member(payload["memberId"])
        if member is None:
            raise Exception("Error getting member object")
        return cls(member=member,
                   registered=payload["registered"],
                   prevData=PlayerData.from_dict(payload["prevData"]),
                   data=PlayerData.from_dict(payload["data"])
                   )
