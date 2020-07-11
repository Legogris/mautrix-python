# Copyright (c) 2020 Tulir Asokan
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from abc import ABC, abstractmethod
import asyncio

from mautrix.types import EventType, StateEvent, Membership

from .syncer import InternalEventType, Syncer


class Dispatcher(ABC):
    syncer: Syncer

    def __init__(self, syncer: Syncer) -> None:
        self.syncer = syncer

    @abstractmethod
    def register(self) -> None:
        pass

    @abstractmethod
    def unregister(self) -> None:
        pass

    def _dispatch(self, event_type: InternalEventType, evt: StateEvent) -> None:
        asyncio.ensure_future(self.syncer.dispatch_manual_event(event_type, evt),
                              loop=self.syncer.loop)


class MembershipEventDispatcher(Dispatcher):
    def register(self) -> None:
        self.syncer.add_event_handler(EventType.ROOM_MEMBER, self.handle)

    def unregister(self) -> None:
        self.syncer.remove_event_handler(EventType.ROOM_MEMBER, self.handle)

    async def handle(self, evt: StateEvent) -> None:
        if evt.type != EventType.ROOM_MEMBER:
            return

        if evt.content.membership == Membership.JOIN:
            if evt.prev_content.membership != Membership.JOIN:
                self._dispatch(InternalEventType.JOIN, evt)
            else:
                self._dispatch(InternalEventType.PROFILE_CHANGE, evt)
        elif evt.content.membership == Membership.INVITE:
            self._dispatch(InternalEventType.INVITE, evt)
        elif evt.content.membership == Membership.LEAVE:
            if evt.prev_content.membership == Membership.BAN:
                self._dispatch(InternalEventType.UNBAN, evt)
            elif evt.prev_content.membership == Membership.INVITE:
                if evt.state_key == evt.sender:
                    self._dispatch(InternalEventType.REJECT_INVITE, evt)
                else:
                    self._dispatch(InternalEventType.DISINVITE, evt)
            elif evt.state_key == evt.sender:
                self._dispatch(InternalEventType.LEAVE, evt)
            else:
                self._dispatch(InternalEventType.KICK, evt)
        elif evt.content.membership == Membership.BAN:
            self._dispatch(InternalEventType.BAN, evt)
