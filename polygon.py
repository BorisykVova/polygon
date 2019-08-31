from typing import Union
import json
import csv
import time

import argparse
from numpy import average
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

MAX_DEPTH = 16
polygon_city_id = {}


class WordsPolygon:
    def __init__(self, polygon: Polygon, father, depth: int, division_by: bool):
        self.polygon = polygon
        self.division_by = division_by  # true - division by horizontally; false division by vertically
        self.depth = depth

        self.city_polygons = []

        # reference to node
        self.father: WordsPolygon = father
        self.left: Union[None, WordsPolygon] = None
        self.right: Union[None, WordsPolygon] = None

    # division of the polygon in half
    def division(self):
        x1, y1, x2, y2 = self.polygon.bounds
        if self.division_by:
            avg = average((x1, x2))
            polygon_l = Polygon([(x1, y1), (x1, y2), (avg, y2), (avg, y1)])
            polygon_r = Polygon([(avg, y1), (avg, y2), (x2, y2), (x2, y1)])
        else:
            avg = average((y1, y2))
            polygon_l = Polygon([(x1, y1), (x1, avg), (x2, avg), (x2, y1)])
            polygon_r = Polygon([(x1, avg), (x1, y2), (x2, y2), (x2, avg)])
        return polygon_l, polygon_r


def build_tress(node: WordsPolygon):

    if node.depth <= MAX_DEPTH:
        polygon_l, polygon_r = node.division()
        node.left = WordsPolygon(polygon_l, node,  node.depth + 1, not node.division_by)
        node.right = WordsPolygon(polygon_r, node, node.depth + 1, not node.division_by)
        build_tress(node.left)
        build_tress(node.right)


def add_city_polygons(polygon: Polygon, node: WordsPolygon):
    if node.left:
        if node.left.polygon.contains(polygon):
            return add_city_polygons(polygon, node.left)
        if node.right.polygon.contains(polygon):
            return add_city_polygons(polygon, node.right)
    node.city_polygons.append(polygon)


def check_point(point: Point, node: WordsPolygon):
    polygon: Polygon
    for polygon in node.city_polygons:
        if polygon.contains(point):
            return polygon_city_id.get(tuple([(x, y) for x, y in zip(*polygon.exterior.xy)]))

    if node.left:
        if node.left.polygon.contains(point):
            return check_point(point, node.left)
        else:
            return check_point(point, node.right)


def load_polygon(file, root: WordsPolygon):
    with open(file) as json_file:
        polygons_json = json.load(json_file)
        for city, polygon_coords in polygons_json.items():
            polygon_coords = tuple([tuple(coords) for coords in polygon_coords])
            polygon = Polygon(polygon_coords)
            polygon_city_id[polygon_coords] = city
            add_city_polygons(polygon, root)


def identification_hotel(file, root: WordsPolygon):
    with open(file, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            try:
                point_coords = [*map(float, (row['longitude'], row['latitude']))]
            except ValueError:
                continue
            point = Point(point_coords)
            city_id = check_point(point, root)
            if city_id:
                with open('result.csv', 'a') as result_file:
                    writer = csv.writer(result_file)
                    writer.writerow((row['hotel_id'], city_id))
            else:
                with open('unidentified_hotel_id.csv', 'a') as unidentified_file:
                    writer = csv.writer(unidentified_file)
                    writer.writerow((row['hotel_id'], ))


def main(polygon_input, hotel_id_input):
    root_polygon = Polygon([(-180, -90), (-180, 90), (180, 90), (180, -90)])
    root = WordsPolygon(root_polygon, None, 1, True)

    print('[*] Build tress')
    build_tress(root)
    print('[*] Load city polygon')
    load_polygon(polygon_input, root)
    print('[*] Hotel identification')

    start = time.time()
    identification_hotel(hotel_id_input, root)
    print(f'Hotel identification time: {time.time() - start}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Help')
    parser.add_argument('--polygon_input', type=str, default='go_test.json', help='Path to json file of polygons')
    parser.add_argument('--hotel_id_input', type=str, default='airbnb_august.csv', help='Path to csv file of hotel id')
    args = parser.parse_args()

    main(args.polygon_input, args.hotel_id_input)
