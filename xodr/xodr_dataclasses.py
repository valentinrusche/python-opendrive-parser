"""
Copyright (C) 2024 Valentin Rusche

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>
"""

import datetime
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class XODRControllerControl:
    signalId: int
    type: str


@dataclass
class XODRController:
    id: int
    name: str
    sequence: int
    controls: List[XODRControllerControl] = field(default_factory=list)


@dataclass
class XODRJunctionController:
    id: int
    type: int
    sequence: int


@dataclass
class XODRJunctionConnectionLaneLink:
    fromId: int
    toId: int


@dataclass
class XODRJunctionConnection:
    id: int
    incomingRoad: int
    connectingRoad: int
    contactPoint: str
    laneLinks: List[XODRJunctionConnectionLaneLink] = field(
        default_factory=list)


@dataclass
class XODRUserDataVectorJunction:
    junctionId: str


@dataclass
class XODRUserDataVectorLane:
    sOffset: float
    laneId: str
    travelDir: str


@dataclass
class XODRUserDataVectorScene:
    program: str
    version: str


@dataclass
class XODRUserDataVectorSignal:
    signalId: str


@dataclass
class XODRUserDataVectorRoad:
    corner: str


@dataclass
class XODRUserData:
    vectorJunction: Optional[XODRUserDataVectorJunction]
    vectorScene: Optional[XODRUserDataVectorScene]
    vectorRoad: Optional[XODRUserDataVectorRoad]
    vectorLanes: List[XODRUserDataVectorLane] = field(default_factory=list)
    vectorSignals: List[XODRUserDataVectorSignal] = field(default_factory=list)


@dataclass
class XODRJunction:
    id: int
    name: str
    userData: Optional[XODRUserData]
    connections: List[XODRJunctionConnection] = field(default_factory=list)
    controllers: List[XODRJunctionController] = field(default_factory=list)


@dataclass
class XODRGeoReference:
    text: str


@dataclass
class XODRHeader:
    revMajor: int
    revMinor: int
    version: int
    date: datetime.datetime
    north: float
    south: float
    east: float
    west: float
    vendor: str
    geoReference: XODRGeoReference
    userData: XODRUserData
    name: str = field(default="")


@dataclass
class XODRRoadLinkPredSucc:
    elementType: str
    elementId: int
    contactPoint: Optional[str]


@dataclass
class XODRRoadLink:
    predecessor: Optional[XODRRoadLinkPredSucc]
    successor: Optional[XODRRoadLinkPredSucc]


@dataclass
class XODRRoadTypeSpeed:
    max: int
    unit: str


@dataclass
class XODRRoadType:
    s: float
    type: str
    speed: XODRRoadTypeSpeed


@dataclass
class XODRRoadPlanViewGeometryLine:
    pass


@dataclass
class XODRRoadPlanViewGeometryArc:
    curvature: float


@dataclass
class XODRRoadPlanViewGeometry:
    s: float
    x: float
    y: float
    hdg: float
    length: float
    line: Optional[XODRRoadPlanViewGeometryLine]
    arc: Optional[XODRRoadPlanViewGeometryArc]


@dataclass
class XODR_SABCD:
    s: float
    a: float
    b: float
    c: float
    d: float


@dataclass
class XODRRoadElevationProfile:
    elevations: List[XODR_SABCD] = field(default_factory=list)


@dataclass
class XODRRoadLateralProfile:
    superelevations: List[XODR_SABCD] = field(default_factory=list)


@dataclass
class XODRRoadPlanView:
    geometry: List[XODRRoadPlanViewGeometry] = field(default_factory=list)


@dataclass
class XODRRoadLaneSectionLCRLaneWidth:
    sOffset: float
    a: float
    b: float
    c: float
    d: float


@dataclass
class XODRRoadLaneSectionLCRLaneRoadMark:
    sOffset: float
    type: str
    material: str
    color: Optional[str]
    laneChange: str
    width: Optional[float]


@dataclass
class XODRRoadLaneSectionLCRLaneLinkPredecessorSuccessor:
    id: int


@dataclass
class XODRRoadLaneSectionLCRLaneLink:
    predecessor: Optional[XODRRoadLaneSectionLCRLaneLinkPredecessorSuccessor]
    successor: Optional[XODRRoadLaneSectionLCRLaneLinkPredecessorSuccessor]


@dataclass
class XODRRoadLaneSectionLCRLane:
    id: int
    type: str
    level: bool
    userData: XODRUserData
    link: XODRRoadLaneSectionLCRLaneLink
    widths: List[XODRRoadLaneSectionLCRLaneWidth] = field(default_factory=list)
    roadMarks: List[XODRRoadLaneSectionLCRLaneRoadMark] = field(
        default_factory=list)


@dataclass
class XODRRoadLaneSectionLCR:
    lanes: List[XODRRoadLaneSectionLCRLane] = field(default_factory=list)


@dataclass
class XODRRoadLaneSection:
    s: float
    left: Optional[XODRRoadLaneSectionLCR]
    center: Optional[XODRRoadLaneSectionLCR]
    right: Optional[XODRRoadLaneSectionLCR]


@dataclass
class XODRRoadLanes:
    laneSection: XODRRoadLaneSection
    laneOffset: List[XODR_SABCD] = field(default_factory=list)


@dataclass
class XODRRoadSignalValidity:
    fromLane: int
    toLane: int


@dataclass
class XODRRoadSignalReference:
    name: Optional[str]
    id: int
    s: float
    t: float
    zOffset: Optional[float]
    hOffset: Optional[float]
    roll: Optional[float]
    pitch: Optional[float]
    orientation: str
    dynamic: Optional[str]
    country: Optional[str]
    type: Optional[int]
    subtype: Optional[int]
    value: Optional[float]
    height: Optional[float]
    width: Optional[float]
    validity: XODRRoadSignalValidity
    userData: XODRUserData
    text: Optional[str]


@dataclass
class XODRRoadObjectsElement:
    id: int
    name: str
    s: float
    t: float
    zOffset: float
    hdg: float
    roll: float
    pitch: float
    orientation: str
    type: str
    height: Optional[float]
    width: float
    length: float


@dataclass
class XODRRoadObjects:
    elements: List[XODRRoadObjectsElement] = field(default_factory=list)


@dataclass
class XODRRoad:
    name: str
    length: float
    id: int
    junction: int
    link: XODRRoadLink
    type: Optional[XODRRoadType]
    planView: XODRRoadPlanView
    elevationProfile: XODRRoadElevationProfile
    lateralProfile: XODRRoadLateralProfile
    lanes: XODRRoadLanes
    objects: Optional[XODRRoadObjects]
    signals: List[XODRRoadSignalReference] = field(default_factory=list)
    signalReferences: List[XODRRoadSignalReference] = field(
        default_factory=list)


@dataclass(eq=True, frozen=True)
class OpenDRIVE:
    header: XODRHeader
    roads: List[XODRRoad] = field(default_factory=list)
    controllers: List[XODRController] = field(default_factory=list)
    junctions: List[XODRJunction] = field(default_factory=list)
