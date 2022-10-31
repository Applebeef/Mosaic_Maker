import glob
import os.path
import numpy as np
import concurrent.futures
from PIL import Image
from scipy import spatial


def importAndResizeTile(tilePath, size, isPortraitBool=False, flip=False):
    tiles = []
    image = Image.open(tilePath)
    image = image.convert('RGB')
    image = image.resize(size)
    if (isPortraitBool and isLandscape(image)) or (not isPortraitBool and imageIsPortrait(image)):
        return None

    tiles.append(image)
    if flip:
        tiles.append(image.rotate(180))
    return tiles


def getColorsFromTiles(tiles):
    colors = []
    for tile in tiles:
        mean_color = np.array(tile).mean(axis=0).mean(axis=0)
        colors.append(mean_color)
    return colors


def imageIsPortrait(image):
    return image.size[1] > image.size[0]


def ratioIsPortrait(ratio):
    return ratio[1] > ratio[0]


def isLandscape(image):
    return image.size[0] > image.size[1]


class MosaicMaker:

    def __init__(self, main_photo_path, tile_folder_path, tile_size_multiplier, tile_size_ratio, epsilon=0.0,
                 main_photo_size_multiplier=1, output_path=None, output_file_name=None, flip=False):
        self.main_photo_path = main_photo_path
        self.tile_size = (tile_size_ratio[0] * tile_size_multiplier, tile_size_ratio[1] * tile_size_multiplier)
        self.epsilon = epsilon
        self.size_increase_multiplier = main_photo_size_multiplier
        self.tile_folder_path = tile_folder_path
        self.output_path = output_path
        self.output_file_name = output_file_name
        self.final_output_path = None
        self.handleOutputPath()

        self.tile_list = []
        self.colors = []
        self.counters = []
        self.tree = None
        self.futures = []
        self.executor = concurrent.futures.ThreadPoolExecutor()
        self.colors_ready = False
        self.is_portrait = ratioIsPortrait(tile_size_ratio)
        self.flip = flip
        self.main_photo = None
        self.resized_photo = None
        self.changed = True

    def handleOutputPath(self):
        if self.output_file_name is None:
            filename = self.main_photo_path.split('\\')[-1].split('.')[0] + '_mosaic.jpg'
        else:
            filename = self.output_file_name

        if self.output_path is None:
            self.final_output_path = filename
        else:
            self.final_output_path = '\\'.join((self.output_path, filename))

    def get_tile_list(self):
        tile_paths = []
        for file in glob.glob(tile_photos_path):
            if file.__contains__("Summary"):
                continue
            if os.path.isfile(file):
                tile_paths.append(file)
        self.futures = [self.executor.submit(importAndResizeTile, path, self.tile_size, self.is_portrait, self.flip) for
                        path in tile_paths]

    def get_colors(self):
        # Calculate dominant color
        for tiles in concurrent.futures.as_completed(self.futures):
            if tiles.result() is None:
                continue
            for tile in tiles.result():
                self.tile_list.append(tile)
                mean_color = np.array(tile).mean(axis=0).mean(axis=0)
                self.colors.append(mean_color)
                self.counters.append(0)
        self.tree = spatial.KDTree(self.colors)
        self.colors_ready = True

    def get_main_photo(self):
        self.main_photo = Image.open(self.main_photo_path)
        self.main_photo = self.main_photo.resize((self.main_photo.size[0] * self.size_increase_multiplier,
                                                  self.main_photo.size[1] * self.size_increase_multiplier))
        width = int(np.round(self.main_photo.size[0] / self.tile_size[0]))
        height = int(np.round(self.main_photo.size[1] / self.tile_size[1]))

        self.resized_photo = self.main_photo.resize((width, height))

    def setup(self):
        self.get_tile_list()
        self.get_colors()
        self.get_main_photo()
        concurrent.futures.wait(self.futures)
        self.changed = False

    def createDeepCopyColors(self):
        temp_colors = []
        for colors in self.colors:
            temp_color = np.copy(colors)
            temp_colors.append(temp_color)
        return temp_colors

    def create_mosaic(self):
        if self.changed:
            self.setup()
        width = self.resized_photo.size[0]
        height = self.resized_photo.size[1]
        mosaic = Image.new('RGB', self.main_photo.size)
        closest_tiles = np.zeros((width, height), dtype=np.uint32)
        temp_colors = self.createDeepCopyColors()
        for i in range(width):
            for j in range(height):
                closest = self.tree.query(self.resized_photo.getpixel((i, j)))
                closest_tiles[i, j] = closest[1]
                temp_colors[closest[1]] = temp_colors[closest[1]] / 1 - self.epsilon * self.counters[closest[1]]
                self.counters[closest[1]] += 1
                temp_colors[closest[1]] = \
                    temp_colors[closest[1]] - temp_colors[closest[1]] * self.epsilon * self.counters[closest[1]]
                self.tree = spatial.KDTree(temp_colors)

        for i in range(width):
            for j in range(height):
                # Offset of tile
                x, y = i * self.tile_size[0], j * self.tile_size[1]
                # Index of tile
                index = closest_tiles[i, j]
                # Draw tile
                mosaic.paste(self.tile_list[index], (x, y))

        mosaic.save(self.final_output_path)
        print(f"Mosaic {self.final_output_path} created")

    def setTileSizeRatio(self, ratio):
        self.tile_size = (ratio[0] * self.tile_size[0], ratio[1] * self.tile_size[1])
        self.changed = True

    def setTileSizeMultiplier(self, multiplier):
        self.tile_size = (multiplier * self.tile_size[0], multiplier * self.tile_size[1])
        self.changed = True

    def setMainPhotoSizeMultiplier(self, multiplier):
        self.size_increase_multiplier = multiplier
        self.changed = True

    def setEpsilon(self, epsilon):
        self.epsilon = epsilon

    def setTileFolder(self, path):
        self.tile_folder_path = path
        self.changed = True

    def setOutputPath(self, path):
        self.output_path = path
        self.handleOutputPath()

    def setOutputFileName(self, name):
        self.output_file_name = name
        self.handleOutputPath()

    def setMainPhotoPath(self, path):
        self.main_photo_path = path
        self.handleOutputPath()
        self.changed = True

    def setFlip(self, flip):
        self.flip = flip
        self.changed = True


if __name__ == "__main__":
    main_photo_path = input("Enter the path to the main photo: ")
    tile_photos_path = input("Enter the path to the tile photos: ")
    tile_photos_path += "\\*"
    tile_size_multiplier = int(input("Enter the tile size multiplier: "))
    tile_size_ratio = (int(input("Enter the tile width ratio: ")), int(input("Enter the tile height ratio: ")))
    epsilon = float(input("Enter the epsilon value: "))
    multiplier = int(input("Enter the main photo size multiplier: "))
    print("\n")
    maker = MosaicMaker(main_photo_path, tile_photos_path, tile_size_multiplier, tile_size_ratio, epsilon, multiplier)
    maker.create_mosaic()
