"""
Copyright (C) 2024 Valentin Rusche

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>
"""

from typing import Any, Callable, List, Union, Set, Tuple
from datetime import datetime
from collections import Counter
import xml.etree.ElementTree as ET

from .xodr_dataclasses import (
    XODR_SABCD,
    OpenDRIVE,
    XODRController,
    XODRControllerControl,
    XODRGeoReference,
    XODRHeader,
    XODRJunction,
    XODRJunctionConnection,
    XODRJunctionConnectionLaneLink,
    XODRJunctionController,
    XODRRoad,
    XODRRoadElevationProfile,
    XODRRoadLaneSection,
    XODRRoadLaneSectionLCR,
    XODRRoadLaneSectionLCRLane,
    XODRRoadLaneSectionLCRLaneLink,
    XODRRoadLaneSectionLCRLaneLinkPredecessorSuccessor,
    XODRRoadLaneSectionLCRLaneRoadMark,
    XODRRoadLaneSectionLCRLaneWidth,
    XODRRoadLanes,
    XODRRoadLateralProfile,
    XODRRoadLink,
    XODRRoadLinkPredSucc,
    XODRRoadObjects,
    XODRRoadObjectsElement,
    XODRRoadPlanView,
    XODRRoadPlanViewGeometry,
    XODRRoadPlanViewGeometryArc,
    XODRRoadPlanViewGeometryLine,
    XODRRoadSignalReference,
    XODRRoadSignalValidity,
    XODRRoadType,
    XODRRoadTypeSpeed,
    XODRUserData,
    XODRUserDataVectorJunction,
    XODRUserDataVectorLane,
    XODRUserDataVectorScene,
    XODRUserDataVectorSignal
)


def map_xml_to_dataclass(xodr_text: str, logger: Any) -> Union[Tuple[OpenDRIVE, List[XODRRoad], Set[int]], None]:
    logger.info("Starting to parse XODR.")
    root: ET.Element = ET.fromstring(text=xodr_text)
    if root.tag is None:
        logger.error("Cannot parse XODR. No valid document root found!")
        return

    xodr_header: Union[XODRHeader, None] = __find_header_data(
        root=root, logger=logger)
    if xodr_header is None:
        logger.error("Cannot parse header from XODR. No valid header found!")
        return

    roads: List[XODRRoad] = __find_list_of_roads(root=root, logger=logger)
    if len(roads) == 0:
        logger.error("Cannot parse roads from XODR. No valid roads found!")
        return

    controllers: List[XODRController] = __find_list_of_controllers(
        root=root, logger=logger)
    if len(controllers) == 0:
        logger.error(
            "Cannot parse controllers from XODR. No valid controllers found!")
        return

    junctions: List[XODRJunction] = __find_list_of_junctions(
        root=root, logger=logger)
    if len(junctions) == 0:
        logger.error(
            "Cannot parse junctions from XODR. No valid junctions found!")
        return

    open_drive_data = OpenDRIVE(
        header=xodr_header,
        roads=roads,
        controllers=controllers,
        junctions=junctions
    )

    logger.info(message=f"Count(road)={len(open_drive_data.roads)}, " +
                f"Count(controller)={len(open_drive_data.controllers)}, " +
                f"Count(junction)={len(open_drive_data.junctions)}")
    road_junction_occurences = Counter(
        road.junction for road in open_drive_data.roads)
    road_junction_count: int = len(road_junction_occurences.values())
    logger.debug(message=f"Road Junction Occurences={
                 road_junction_occurences}")
    logger.debug(message=f"Count(Road Junction)={
                 road_junction_count}. Count(Junction ID != -1): {road_junction_count-1}")
    filtered_roads, removed_roads = __filter_unnessecary_roads(
        roads=open_drive_data.roads, logger=logger)
    filtered_roads: List[XODRRoad] = __filter_unnessecary_lanes(
        roads=filtered_roads)
    return open_drive_data, filtered_roads, removed_roads


# stars doesnt care about these lanes..
def __filter_unnessecary_lanes(roads: List[XODRRoad]) -> List[XODRRoad]:
    lane_filtered_roads: List[XODRRoad] = []
    for road in roads:
        if road.lanes is not None and road.lanes.laneSection is not None:
            for lane_section in [road.lanes.laneSection.left, road.lanes.laneSection.center, road.lanes.laneSection.right]:
                if lane_section is not None:
                    lane_section.lanes = [lane for lane in lane_section.lanes if lane.type.lower(
                    ) not in ["sidewalk", "none", "shoulder", "median"]]
        lane_filtered_roads.append(road)
    return lane_filtered_roads


def __filter_unnessecary_roads(roads: List[XODRRoad], logger: Any) -> Tuple[List[XODRRoad], Set[int]]:
    logger.info(
        message="Filtering roads (removing types: sidewalk, none, shoulder, median)")
    filtered_roads: List[XODRRoad] = []
    for road in roads:
        if road.lanes is not None and road.lanes.laneSection is not None:
            # we can stop the iteration early and move to the next step
            # of the outer loop if one condition is met
            _ = [__apply_filter(filtered_roads=filtered_roads, road=road, lane_section=lane_section)
                 for lane_section in [road.lanes.laneSection.left, road.lanes.laneSection.center, road.lanes.laneSection.right]
                 if lane_section is not None and road not in filtered_roads]
    removed_roads = set(
        road.id for road in roads if road not in filtered_roads)
    removed_road_count: int = len(removed_roads)
    filtered_road_count: int = len(filtered_roads)
    logger.info(message=f"Count(Removed Road)={removed_road_count}")
    logger.debug(message=f"Removed road ids: [{
                 ', '.join(str(id) for id in sorted(removed_roads))}]")
    logger.info(message=f"Count(Filtered Road)={filtered_road_count}")
    return filtered_roads, removed_roads


def __apply_filter(filtered_roads: List[XODRRoad], road: XODRRoad, lane_section: XODRRoadLaneSectionLCR) -> None:
    interested_in_type: Callable[[str], bool] = lambda type: type.lower() not in [
        "sidewalk", "none", "shoulder", "median"]
    for lane in lane_section.lanes:
        if interested_in_type(type=lane.type):
            filtered_roads.append(road)
            return


def __find_header_data(root: ET.Element, logger: Any) -> Union[XODRHeader, None]:
    xml_header: Union[ET.Element, None] = root.find(path="./header")
    if xml_header is None:
        logger.error("No header subtree found. Exiting!")
        return None

    rev_major: str = xml_header.attrib["revMajor"]
    rev_minor: str = xml_header.attrib["revMinor"]
    version: str = xml_header.attrib["version"]
    date: str = xml_header.attrib["date"]
    north: str = xml_header.attrib["north"]
    south: str = xml_header.attrib["south"]
    east: str = xml_header.attrib["east"]
    west: str = xml_header.attrib["west"]
    vendor: str = xml_header.attrib["vendor"]
    name: str = xml_header.attrib["name"]

    xml_geo_reference: Union[ET.Element,
                             None] = xml_header.find(path="./geoReference")
    if xml_geo_reference is None:
        logger.error("No geo reference found. Exiting!")
        return None
    xml_geo_reference_text: Union[str, None] = xml_geo_reference.text
    if xml_geo_reference_text is None:
        logger.error("No geo reference data found. Exiting!")
        return None

    xml_user_data: Union[ET.Element, None] = xml_header.find(path="./userData")
    if xml_user_data is None:
        logger.error("No user data found. Exiting!")
        return None

    xml_user_data_vector_scene: Union[ET.Element,
                                      None] = xml_user_data.find("./vectorScene")
    if xml_user_data_vector_scene is None:
        logger.error("No vector scene found. Exiting!")
        return None

    xml_program: str = xml_user_data_vector_scene.attrib["program"]
    xml_version: str = xml_user_data_vector_scene.attrib["version"]

    return XODRHeader(
        revMajor=int(rev_major),
        revMinor=int(rev_minor),
        version=int(version),
        date=datetime.strptime(date, '%Y-%m-%dT%H:%M:%S'),
        north=float(north),
        south=float(south),
        east=float(east),
        west=float(west),
        vendor=vendor,
        geoReference=XODRGeoReference(text=xml_geo_reference_text),
        userData=XODRUserData(
            vectorJunction=None,
            vectorScene=XODRUserDataVectorScene(
                program=xml_program,
                version=xml_version
            ),
            vectorSignals=[],
            vectorLanes=[],
            vectorRoad=None
        ),
        name=name
    )


def __find_list_of_roads(root: ET.Element, logger: Any) -> List[XODRRoad]:
    road_list: List[XODRRoad] = []

    # Fail fast
    list_of_xml_roads: List[ET.Element] = root.findall(path="./road")
    if len(list_of_xml_roads) == 0:
        logger.error("No road subtree found. Exiting!")
        return road_list

    for road in list_of_xml_roads:
        name: Union[str, None] = road.attrib["name"]
        road_id: Union[str, None] = road.attrib["id"]
        length: Union[str, None] = road.attrib["length"]
        junction: Union[str, None] = road.attrib["junction"]

        if name is None or road_id is None or length is None or junction is None:
            logger.error("Invalid controller. Exiting!")
            return road_list

        xodr_road_link: XODRRoadLink = __get_road_link(road=road)

        xodr_road_type: Union[XODRRoadType, None] = __get_road_type(road=road)

        xodr_road_plan_view: Union[XODRRoadPlanView, None] = __get_road_plan_view(
            road=road, logger=logger)
        if xodr_road_plan_view is None:
            logger.error("Invalid road. Exiting!")
            return road_list

        xodr_road_elevation_profile: Union[XODRRoadElevationProfile,
                                           None] = __get_road_elevation_profile(road=road, logger=logger)
        if xodr_road_elevation_profile is None:
            logger.error("Invalid road elevation profile. Exiting!")
            return road_list

        xodr_road_lateral_profile: Union[XODRRoadLateralProfile, None] = __get_road_lateral_profile(
            road=road, logger=logger)
        if xodr_road_lateral_profile is None:
            logger.error("Invalid road lateral profile. Exiting!")
            return road_list

        xodr_road_lanes: Union[XODRRoadLanes, None] = __get_road_lanes(
            road=road, logger=logger)
        if xodr_road_lanes is None:
            logger.error("Invalid road road lanes. Exiting!")
            return road_list

        xodr_road_signals: List[XODRRoadSignalReference] = __get_road_signals(
            road=road, is_reference=False)
        xodr_road_signal_references: List[XODRRoadSignalReference] = __get_road_signals(
            road=road, is_reference=True)
        xodr_road_objects: Union[XODRRoadObjects,
                                 None] = __get_road_objects(road=road)
        road_list.append(
            XODRRoad(
                elevationProfile=xodr_road_elevation_profile,
                id=int(road_id),
                junction=int(junction),
                lanes=xodr_road_lanes,
                lateralProfile=xodr_road_lateral_profile,
                length=float(length),
                link=xodr_road_link,
                name=name,
                objects=xodr_road_objects,
                planView=xodr_road_plan_view,
                signalReferences=xodr_road_signal_references,
                signals=xodr_road_signals,
                type=xodr_road_type
            )
        )
    return road_list


def __get_road_objects(road: ET.Element) -> Union[XODRRoadObjects, None]:
    xml_objects: Union[ET.Element, None] = road.find(path="./objects")
    if xml_objects is None:
        return None

    xodr_object_elements: List[XODRRoadObjectsElement] = []

    for obj in xml_objects.findall(path="./object"):
        xodr_object_elements.append(XODRRoadObjectsElement(
            hdg=float(obj.attrib["hdg"]),
            height=float(obj.attrib["height"]
                         ) if "height" in obj.attrib else None,
            id=int(obj.attrib["id"]),
            length=float(obj.attrib["length"]),
            name=obj.attrib["name"],
            orientation=obj.attrib["orientation"],
            pitch=float(obj.attrib["pitch"]),
            roll=float(obj.attrib["roll"]),
            s=float(obj.attrib["s"]),
            t=float(obj.attrib["t"]),
            type=obj.attrib["type"],
            width=float(obj.attrib["width"]),
            zOffset=float(obj.attrib["zOffset"]),
        ))
    return XODRRoadObjects(elements=xodr_object_elements)


def __get_road_signals(road: ET.Element, is_reference: bool) -> List[XODRRoadSignalReference]:
    road_signals: List[XODRRoadSignalReference] = []

    xml_signals: List[ET.Element] = road.findall(
        path="./signals/signal") if not is_reference else road.findall(path="./signals/signalReference")
    if xml_signals is None or len(xml_signals) == 0:
        # we just dont have any signals
        return road_signals

    for signal in xml_signals:
        signal_id: str = signal.attrib["id"]
        s: str = signal.attrib["t"]
        t: str = signal.attrib["s"]
        orientation: str = signal.attrib["orientation"]

        xml_user_data: Union[ET.Element, None] = signal.find(path="./userData")
        if xml_user_data is None:
            return road_signals
        xodr_vector_signals: List[XODRUserDataVectorSignal] = []
        xml_user_data_vector_signals: List[ET.Element] = xml_user_data.findall(
            "./vectorSignal")
        if xml_user_data_vector_signals is not None and len(xml_user_data_vector_signals) != 0:
            for vector_signal in xml_user_data_vector_signals:
                if "signalId" in vector_signal.attrib:
                    xodr_vector_signals.append(XODRUserDataVectorSignal(
                        signalId=vector_signal.attrib["signalId"]
                    ))

        xodr_user_data = XODRUserData(
            vectorJunction=None,
            vectorLanes=[],
            vectorRoad=None,
            vectorScene=None,
            vectorSignals=xodr_vector_signals
        )

        xml_validity: Union[ET.Element, None] = signal.find(path="./validity")
        if xml_validity is None:
            return road_signals

        xodr_validity: XODRRoadSignalValidity = XODRRoadSignalValidity(
            fromLane=int(xml_validity.attrib["fromLane"]),
            toLane=int(xml_validity.attrib["toLane"])
        )

        xodr_signal = XODRRoadSignalReference(
            id=int(signal_id),
            s=float(s),
            t=float(t),
            orientation=orientation,
            country=None,
            dynamic=None,
            height=None,
            hOffset=None,
            name=None,
            pitch=None,
            roll=None,
            subtype=None,
            text=None,
            type=None,
            value=None,
            width=None,
            zOffset=None,
            userData=xodr_user_data,
            validity=xodr_validity,
        )

        if 'country' in signal.attrib:
            xodr_signal.country = signal.attrib["country"]
        if 'dynamic' in signal.attrib:
            xodr_signal.dynamic = signal.attrib["dynamic"]
        if 'height' in signal.attrib:
            xodr_signal.height = float(signal.attrib["height"])
        if 'hOffset' in signal.attrib:
            xodr_signal.hOffset = float(signal.attrib["hOffset"])
        if 'name' in signal.attrib:
            xodr_signal.name = signal.attrib["name"]
        if 'pitch' in signal.attrib:
            xodr_signal.pitch = float(signal.attrib["pitch"])
        if 'roll' in signal.attrib:
            xodr_signal.roll = float(signal.attrib["roll"])
        if 'subtype' in signal.attrib:
            xodr_signal.subtype = int(signal.attrib["subtype"])
        if 'value' in signal.attrib:
            xodr_signal.value = float(signal.attrib["value"])
        if 'width' in signal.attrib:
            xodr_signal.width = float(signal.attrib["width"])
        if 'type' in signal.attrib:
            xodr_signal.type = int(signal.attrib["type"])
        if 'zOffset' in signal.attrib:
            xodr_signal.zOffset = float(signal.attrib["zOffset"])
        if 'text' in signal.attrib:
            xodr_signal.text = signal.attrib["text"]
        road_signals.append(xodr_signal)

    return road_signals


def __get_road_lanes(road: ET.Element, logger: Any) -> Union[XODRRoadLanes, None]:
    xml_road_lanes: Union[ET.Element, None] = road.find(path="./lanes")

    if xml_road_lanes is None:
        logger.error("No lanes found. Exiting!")
        return None

    xodr_lane_offsets: List[XODR_SABCD] = __get_road_lane_offsets(
        logger=logger, xml_road_lanes=xml_road_lanes)

    if xodr_lane_offsets is None or len(xodr_lane_offsets) == 0:
        logger.error("No lane offsets found. Exiting!")
        return None

    xodr_lane_section: Union[XODRRoadLaneSection, None] = __get_road_lane_section(
        logger=logger, xml_road_lanes=xml_road_lanes)
    if xodr_lane_section is None:
        logger.error("No lane section found. Exiting!")
        return None

    return XODRRoadLanes(
        laneOffset=xodr_lane_offsets,
        laneSection=xodr_lane_section
    )


def __get_road_lane_section(xml_road_lanes: ET.Element, logger: Any) -> Union[XODRRoadLaneSection, None]:
    xml_lane_section: Union[ET.Element,
                            None] = xml_road_lanes.find(path="./laneSection")

    if xml_lane_section is None:
        return None

    s: str = xml_lane_section.attrib["s"]

    xodr_section = XODRRoadLaneSection(
        s=float(s), left=None, center=None, right=None)

    left: Union[ET.Element, None] = xml_lane_section.find(path="./left")
    if left is not None:
        xodr_section.left = __get_lane_section_lane_info(
            lane=left, logger=logger)
    center: Union[ET.Element, None] = xml_lane_section.find(path="./center")
    if center is not None:
        xodr_section.center = __get_lane_section_lane_info(
            lane=center, logger=logger)
    right: Union[ET.Element, None] = xml_lane_section.find(path="./right")
    if right is not None:
        xodr_section.right = __get_lane_section_lane_info(
            lane=right, logger=logger)
    return xodr_section


def __get_lane_section_lane_info(lane: ET.Element, logger: Any) -> Union[XODRRoadLaneSectionLCR, None]:
    xodr_lanes: List[XODRRoadLaneSectionLCRLane] = []
    xml_lanes: List[ET.Element] = lane.findall(path="./lane")

    if xml_lanes is not None and len(xml_lanes) != 0:
        for lcr_lane in xml_lanes:
            lane_id: str = lcr_lane.attrib["id"]
            lane_type: str = lcr_lane.attrib["type"]
            level: str = lcr_lane.attrib["level"]

            xml_user_data: Union[ET.Element,
                                 None] = lcr_lane.find(path="./userData")
            if xml_user_data is None:
                logger.error("No lane user data found. Exiting!")
                return None
            xml_user_data_vector_lanes: List[ET.Element] = xml_user_data.findall(
                path="./vectorLanes")
            xodr_vector_lanes: List[XODRUserDataVectorLane] = []
            if xml_user_data_vector_lanes is not None and len(xml_user_data_vector_lanes) != 0:
                for elem in xml_user_data_vector_lanes:
                    vector_lane = XODRUserDataVectorLane(
                        sOffset=float(elem.attrib["sOffset"]),
                        laneId=elem.attrib["laneId"],
                        travelDir=elem.attrib["travelDir"]
                    )
                    xodr_vector_lanes.append(vector_lane)
            xodr_user_data = XODRUserData(
                vectorJunction=None,
                vectorLanes=xodr_vector_lanes,
                vectorRoad=None,
                vectorScene=None,
                vectorSignals=[]
            )
            xodr_widths: List[XODRRoadLaneSectionLCRLaneWidth] = []
            xml_widths: List[ET.Element] = lcr_lane.findall(path="./width")
            if xml_widths is not None and len(xml_widths) != 0:
                for elem in xml_widths:
                    xodr_widths.append(
                        XODRRoadLaneSectionLCRLaneWidth(
                            sOffset=float(elem.attrib["sOffset"]),
                            a=float(elem.attrib["a"]),
                            b=float(elem.attrib["b"]),
                            c=float(elem.attrib["c"]),
                            d=float(elem.attrib["d"])
                        )
                    )

            road_marks: List[XODRRoadLaneSectionLCRLaneRoadMark] = []
            xml_marks: List[ET.Element] = lcr_lane.findall(path="./roadMark")
            if xml_marks is not None and len(xml_marks) != 0:
                for elem in xml_marks:
                    xodr_mark = XODRRoadLaneSectionLCRLaneRoadMark(
                        sOffset=float(elem.attrib["sOffset"]),
                        type=elem.attrib["type"],
                        material=elem.attrib["material"],
                        color=None,
                        laneChange=elem.attrib["laneChange"],
                        width=None
                    )
                    if 'color' in elem.attrib:
                        xodr_mark.color = elem.attrib["color"]
                    if 'width' in elem.attrib:
                        xodr_mark.width = float(elem.attrib["width"])
                    road_marks.append(xodr_mark)

            xml_link: Union[ET.Element, None] = lcr_lane.find(path="./link")
            lane_link = XODRRoadLaneSectionLCRLaneLink(
                predecessor=None,
                successor=None
            )
            if xml_link is not None:
                xml_link_pred: Union[ET.Element, None] = xml_link.find(
                    path="./predecessor")
                if xml_link_pred is not None:
                    pred_id: int = int(xml_link_pred.attrib["id"])
                    lane_link.predecessor = XODRRoadLaneSectionLCRLaneLinkPredecessorSuccessor(
                        id=pred_id)
                xml_link_succ: Union[ET.Element, None] = xml_link.find(
                    path="./successor")
                if xml_link_succ is not None:
                    succ_id: int = int(xml_link_succ.attrib["id"])
                    lane_link.successor = XODRRoadLaneSectionLCRLaneLinkPredecessorSuccessor(
                        id=succ_id)

            xodr_lcr_lane: XODRRoadLaneSectionLCRLane = XODRRoadLaneSectionLCRLane(
                id=int(lane_id),
                type=lane_type,
                level=bool(level),
                userData=xodr_user_data,
                roadMarks=road_marks,
                widths=xodr_widths,
                link=lane_link
            )
            xodr_lanes.append(xodr_lcr_lane)
    return XODRRoadLaneSectionLCR(lanes=xodr_lanes)


def __get_road_lane_offsets(xml_road_lanes: ET.Element, logger: Any) -> List[XODR_SABCD]:
    xodr_lane_offsets: List[XODR_SABCD] = []
    xml_lane_offsets: List[ET.Element] = xml_road_lanes.findall(
        path="./laneOffset")
    if xml_lane_offsets is None or len(xml_lane_offsets) == 0:
        logger.error("No lane offset found. Exiting!")
        return xodr_lane_offsets

    for offset in xml_lane_offsets:
        s: str = offset.attrib["s"]
        a: str = offset.attrib["a"]
        b: str = offset.attrib["b"]
        c: str = offset.attrib["c"]
        d: str = offset.attrib["d"]
        xodr_lane_offsets.append(
            XODR_SABCD(
                s=float(s),
                a=float(a),
                b=float(b),
                c=float(c),
                d=float(d)
            )
        )
    return xodr_lane_offsets


def __get_road_lateral_profile(road: ET.Element, logger: Any) -> Union[XODRRoadLateralProfile, None]:
    xml_road_lateral_profile: Union[ET.Element,
                                    None] = road.find(path="./elevationProfile")
    xodr_super_elevations: List[XODR_SABCD] = []

    if xml_road_lateral_profile is None:
        logger.error("No lateral profile found. Exiting!")
        return None

    if xml_road_lateral_profile.find(path="./superelevation") is None:
        # return an empty lateral profile
        return XODRRoadLateralProfile(superelevations=xodr_super_elevations)

    # type: ignore # cannot be None here..
    for elevation in xml_road_lateral_profile.find(path="./superelevation"):
        s: str = elevation.attrib["s"]
        a: str = elevation.attrib["a"]
        b: str = elevation.attrib["b"]
        c: str = elevation.attrib["c"]
        d: str = elevation.attrib["d"]
        xodr_super_elevations.append(XODR_SABCD(
            s=float(s),
            a=float(a),
            b=float(b),
            c=float(c),
            d=float(d),
        ))
    return XODRRoadLateralProfile(superelevations=xodr_super_elevations)


def __get_road_elevation_profile(road: ET.Element, logger: Any) -> Union[XODRRoadElevationProfile, None]:
    xml_road_elevation_profile: Union[ET.Element, None] = road.find(
        path="./elevationProfile")
    xodr_elevations: List[XODR_SABCD] = []

    if xml_road_elevation_profile is None:
        logger.error("No elevation profile found. Exiting!")
        return None

    # type: ignore # cannot be None here..
    for elevation in xml_road_elevation_profile.find(path="./elevation"):
        s: str = elevation.attrib["s"]
        a: str = elevation.attrib["a"]
        b: str = elevation.attrib["b"]
        c: str = elevation.attrib["c"]
        d: str = elevation.attrib["d"]
        xodr_elevations.append(XODR_SABCD(
            s=float(s),
            a=float(a),
            b=float(b),
            c=float(c),
            d=float(d),
        ))
    return XODRRoadElevationProfile(elevations=xodr_elevations)


def __get_road_plan_view(road: ET.Element, logger: Any) -> Union[XODRRoadPlanView, None]:
    xml_road_plan_view: Union[ET.Element, None] = road.find(path="./planView")
    xodr_geometries: List[XODRRoadPlanViewGeometry] = []

    if xml_road_plan_view is None or len(xml_road_plan_view) == 0:
        logger.error("No plan view found. Exiting!")
        return None

    for geometry in xml_road_plan_view:
        xodr_geo: XODRRoadPlanViewGeometry = XODRRoadPlanViewGeometry(
            s=0.0,
            x=0.0,
            y=0.0,
            hdg=0.0,
            length=0.0,
            line=None,
            arc=None
        )
        if 's' in geometry.attrib:  # will include all attribs or None at all, so checking for 's' suffices
            s: str = geometry.attrib["s"]
            x: str = geometry.attrib["x"]
            y: str = geometry.attrib["y"]
            hdg: str = geometry.attrib["hdg"]
            length: str = geometry.attrib["length"]

            xodr_geo.s = float(s)
            xodr_geo.x = float(x)
            xodr_geo.y = float(y)
            xodr_geo.hdg = float(hdg)
            xodr_geo.length = float(length)
        if geometry is not None:
            lines: Union[ET.Element, None] = geometry.find(path="./line")
            arcs: Union[ET.Element, None] = geometry.find(path="./arc")
            if lines is not None and len(lines) != 0:
                for _ in lines:
                    xodr_geo.line = XODRRoadPlanViewGeometryLine()
            if arcs is not None and len(arcs) != 0:
                for arc in arcs:
                    curv: str = arc.attrib["curvature"]
                    xodr_geo.arc = XODRRoadPlanViewGeometryArc(
                        curvature=float(curv))
        xodr_geometries.append(xodr_geo)
    return XODRRoadPlanView(geometry=xodr_geometries)


def __get_road_type(road: ET.Element) -> Union[XODRRoadType, None]:
    xml_road_type: Union[ET.Element, None] = road.find(path="./type")

    if xml_road_type is not None:
        s: str = xml_road_type.attrib["s"]
        road_type: str = xml_road_type.attrib["type"]
        xml_speed: Union[ET.Element, None] = xml_road_type.find(path="./speed")
        if xml_speed is not None:
            xml_speed_max: str = xml_speed.attrib["max"]
            xml_speed_unit: str = xml_speed.attrib["unit"]

            return XODRRoadType(
                s=float(s),
                type=road_type,
                speed=XODRRoadTypeSpeed(
                    max=int(xml_speed_max),
                    unit=xml_speed_unit
                )
            )
    return None


def __get_road_link(road: ET.Element) -> XODRRoadLink:
    xml_road_link_pred: Union[ET.Element, None] = road.find(
        path="./link/predecessor")
    xml_road_link_pred_element_type: str = ""
    xml_road_link_pred_element_id: str = ""
    xml_road_link_pred_contact_point: str = ""
    if xml_road_link_pred is not None:
        xml_road_link_pred_element_type: str = xml_road_link_pred.attrib["elementType"]
        xml_road_link_pred_element_id: str = xml_road_link_pred.attrib["elementId"]
        if 'contactPoint' in xml_road_link_pred.attrib:
            xml_road_link_pred_contact_point: str = xml_road_link_pred.attrib["contactPoint"]

    xml_road_link_succ: Union[ET.Element, None] = road.find(
        path="./link/successor")
    xml_road_link_succ_element_type: str = ""
    xml_road_link_succ_element_id: str = ""
    xml_road_link_succ_contact_point: str = ""
    if xml_road_link_succ is not None:
        xml_road_link_succ_element_type: str = xml_road_link_succ.attrib["elementType"]
        xml_road_link_succ_element_id: str = xml_road_link_succ.attrib["elementId"]
        if 'contactPoint' in xml_road_link_succ.attrib:
            xml_road_link_pred_contact_point: str = xml_road_link_succ.attrib["contactPoint"]

    xodr_road_link: XODRRoadLink = XODRRoadLink(
        predecessor=XODRRoadLinkPredSucc(
            elementType=xml_road_link_pred_element_type,
            elementId=int(xml_road_link_pred_element_id),
            contactPoint=xml_road_link_pred_contact_point if xml_road_link_pred_contact_point != "" else None
        ) if xml_road_link_pred_element_id != "" else None,
        successor=XODRRoadLinkPredSucc(
            elementType=xml_road_link_succ_element_type,
            elementId=int(xml_road_link_succ_element_id),
            contactPoint=xml_road_link_succ_contact_point if xml_road_link_succ_contact_point != "" else None
        ) if xml_road_link_succ_element_id != "" else None
    )
    return xodr_road_link


def __find_list_of_controllers(root: ET.Element, logger: Any) -> List[XODRController]:
    controller_list: List[XODRController] = []

    # Fail fast
    list_of_xml_controllers: List[ET.Element] = root.findall(
        path="./controller")
    if len(list_of_xml_controllers) == 0:
        logger.error("No controller subtree found. Exiting!")
        return controller_list

    for controller in list_of_xml_controllers:
        name: Union[str, None] = controller.attrib["name"]
        controller_id: Union[str, None] = controller.attrib["id"]
        sequence: Union[str, None] = controller.attrib["sequence"]
        if name is None or controller_id is None or sequence is None:
            logger.error("Invalid controller. Exiting!")
            return controller_list

        control_list: List[XODRControllerControl] = []
        for control in controller.findall(path="./control"):
            signal_id: Union[str, None] = control.attrib["signalId"]
            control_type: Union[str, None] = control.attrib["type"]
            if signal_id is None or control_type is None:
                logger.error("Invalid control. Exiting!")
                return controller_list

            dataclass_control: XODRControllerControl = XODRControllerControl(
                signalId=int(signal_id),
                type=control_type
            )
            control_list.append(dataclass_control)
        xodr_controller = XODRController(
            id=int(controller_id),
            name=name,
            sequence=int(sequence),
            controls=control_list
        )
        controller_list.append(xodr_controller)
    return controller_list


def __find_list_of_junctions(root: ET.Element, logger: Any) -> List[XODRJunction]:
    junction_list: List[XODRJunction] = []

    # Fail fast
    list_of_xml_junctions: List[ET.Element] = root.findall(path="./junction")
    if len(list_of_xml_junctions) == 0:
        logger.error("No junction subtree found. Exiting!")
        return junction_list

    for junction in list_of_xml_junctions:
        junction_id: Union[str, None] = junction.attrib["id"]
        junction_name: Union[str, None] = junction.attrib["name"]
        if junction_id is None or junction_name is None:
            logger.error("Invalid junction. Exiting!")
            return junction_list

        list_of_connections: List[XODRJunctionConnection] = []
        list_of_controllers: List[XODRJunctionController] = []
        for connection in junction.findall(path="./connection"):
            list_of_lanelinks: List[XODRJunctionConnectionLaneLink] = []
            for lanelink in connection.findall(path="./laneLink"):
                _from: str = lanelink.attrib["from"]
                _to: str = lanelink.attrib["to"]
                if _from is None or _to is None:
                    logger.error("Invalid Lanelink. Exiting!")
                    return junction_list

                ll = XODRJunctionConnectionLaneLink(
                    fromId=int(_from), toId=int(_to))
                list_of_lanelinks.append(ll)
            connection_id: Union[str, None] = connection.attrib["id"]
            incoming_road: Union[str, None] = connection.attrib["incomingRoad"]
            connecting_road: Union[str,
                                   None] = connection.attrib["connectingRoad"]
            contact_point: Union[str, None] = connection.attrib["contactPoint"]
            if connection_id is None or incoming_road is None or connecting_road is None or contact_point is None:
                logger.error("Invalid connection at junction. Exiting!")
                return junction_list

            junction_connection: XODRJunctionConnection = XODRJunctionConnection(
                id=int(connection_id),
                incomingRoad=int(incoming_road),
                connectingRoad=int(connecting_road),
                contactPoint=contact_point,
                laneLinks=list_of_lanelinks
            )
            list_of_connections.append(junction_connection)
        xodr_junction: XODRJunction = XODRJunction(
            id=int(junction_id),
            name=junction_name,
            userData=None,
            connections=list_of_connections,
            controllers=list_of_controllers
        )
        vector_junction: Union[ET.Element, None] = junction.find(
            path="./userData/vectorJunction")
        if vector_junction is not None:
            junction_id = vector_junction.attrib["junctionId"]
            user_data = XODRUserData(vectorJunction=XODRUserDataVectorJunction(
                junctionId=junction_id),
                vectorScene=None,
                vectorSignals=[],
                vectorRoad=None
            )
            xodr_junction.userData = user_data
        junction_list.append(xodr_junction)
    return junction_list
