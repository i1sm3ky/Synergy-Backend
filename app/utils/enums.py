from enum import Enum


class Role(str, Enum):
    EMPLOYEE = "employee"
    EMPLOYER = "employer"


class WorkStatus(str, Enum):
    OFFICE = "office"
    WFH = "wfh"
    LEAVE = "leave"
    NULL = "null"


class WorkspaceType(str, Enum):
    WORK_STATION = "work_station"
    HOT_SEAT = "hot_seat"
    DISCUSSION_ROOM = "discussion_room"


class BookingPattern(str, Enum):
    MO = "mo"
    TU = "tu"
    WE = "we"
    TH = "th"
    FR = "fr"
    SA = "sa"
    SU = "su"
