import glob
import os.path
import numpy as np
import concurrent.futures
from PIL import Image
from scipy import spatial
import sqlite3


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


def printMenu():
    print("1. Select main image")
    print("2. Select folder for tile images")
    print("3. Select multiplier for the tile size")
    print("4. Select the ratios for the tiles")
    print("5. Select the epsilon used for limiting repeats of tiles (optional)")
    print("6. Select the multiplier for the \"upscaling\" of the main image (optional)")
    print("7. Select output file name (optional)")
    print("8. Select output folder (optional)")
    print("9. Run mosaic maker")
    print("10. Database menu")
    print("11. Exit")
    print("Choose an option: ", end='')


def printDatabaseMenu():
    print("1. Save current settings to database")
    print("2. Load settings from database")
    print("3. Delete settings from database")
    print("4. Show all settings in database")
    print("5. Exit")


def isReadyCheck(main_photo, tiles, tile_multiplier, ratios):
    return main_photo[0] is not None and \
           tiles[0] is not None and \
           tile_multiplier[0] is not None and \
           ratios[0] is not None


def saveSettings(main_photo, tiles, tile_multiplier, ratios, epsilon, upscaling_multiplier, output_file_name,
                 output_folder, name):
    conn = sqlite3.connect('settings.db')
    c = conn.cursor()
    create_table = """CREATE TABLE IF NOT EXISTS settings (
                        setting_name text NOT NULL PRIMARY KEY,
                        main_photo text,
                        tiles text,
                        tile_multiplier integer,
                        width integer,
                        height integer,
                        epsilon real,
                        upscaling_multiplier integer,
                        output_file_name text,
                        output_folder text
                    );"""
    c.execute(create_table)
    insert = """INSERT INTO settings (setting_name, main_photo, tiles, tile_multiplier, width, height, epsilon, upscaling_multiplier, output_file_name, output_folder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    c.execute(insert, (
        name,
        main_photo,
        tiles,
        tile_multiplier,
        ratios[0],
        ratios[1],
        epsilon,
        upscaling_multiplier,
        output_file_name,
        output_folder))
    conn.commit()
    conn.close()


def loadSettings(name):
    conn = sqlite3.connect('settings.db')
    c = conn.cursor()
    select = """SELECT * FROM settings WHERE setting_name = ?"""
    c.execute(select, (name,))
    result = c.fetchone()
    conn.close()
    return result


def deleteSettings(name):
    conn = sqlite3.connect('settings.db')
    c = conn.cursor()
    delete = """DELETE FROM settings WHERE setting_name = ?"""
    c.execute(delete, (name,))
    conn.commit()
    conn.close()


def printSettings():
    conn = sqlite3.connect('settings.db')
    c = conn.cursor()
    select = """SELECT * FROM settings"""
    c.execute(select)
    result = c.fetchall()
    conn.close()
    for row in result:
        print(row)


def main():
    main_photo_path = [None, False]
    tile_photos_path = [None, False]
    tile_size_multiplier = [None, False]
    tile_size_ratio = [None, False]
    epsilon = [0, False]
    main_photo_size_multiplier = [None, False]
    output_file_name = [None, False]
    output_folder = [None, False]
    isReady = False
    maker = None
    while True:
        print("Current settings:")
        print("Main photo path: " + str(main_photo_path[0]))
        print("Tile photos path: " + str(tile_photos_path[0]))
        print("Tile size multiplier: " + str(tile_size_multiplier[0]))
        print("Tile size ratio: " + str(tile_size_ratio[0]))
        print("Epsilon: " + str(epsilon[0]))
        print("Main photo size multiplier: " + str(main_photo_size_multiplier[0]))
        print("Output file name: " + str(output_file_name[0]))
        print("Output folder: " + str(output_folder[0]))
        printMenu()
        option = input()
        match option:
            case '1':
                print("Enter the path to the main image: ", end='')
                main_photo_path[0] = input()
                main_photo_path[1] = True
                isReady = isReadyCheck(main_photo_path, tile_photos_path, tile_size_multiplier, tile_size_ratio)
            case '2':
                print("Enter the path to the folder with the tile images: ", end='')
                tile_photos_path[0] = input()
                tile_photos_path[0] = '\\'.join((tile_photos_path[0], '*'))
                tile_photos_path[1] = True
                isReady = isReadyCheck(main_photo_path, tile_photos_path, tile_size_multiplier, tile_size_ratio)
            case '3':
                print("Enter the multiplier for the tile size: ", end='')
                tile_size_multiplier[0] = int(input())
                tile_size_multiplier[1] = True
                isReady = isReadyCheck(main_photo_path, tile_photos_path, tile_size_multiplier, tile_size_ratio)
            case '4':
                print("Enter the ratios for the tiles (in the format of width:height e.g. 1:1, 2:3, 3:2): ", end='')
                tile_size_ratio[0] = input()
                tile_size_ratio[0] = tile_size_ratio[0].split(':')
                tile_size_ratio[0] = (int(tile_size_ratio[0][0]), int(tile_size_ratio[0][1]))
                tile_size_ratio[1] = True
                isReady = isReadyCheck(main_photo_path, tile_photos_path, tile_size_multiplier, tile_size_ratio)
            case '5':
                print("Enter the epsilon used for limiting repeats of tiles: ", end='')
                epsilon[0] = float(input())
                epsilon[1] = True
            case '6':
                print("Enter the multiplier for the \"upscaling\" of the main image: ", end='')
                main_photo_size_multiplier[0] = int(input())
                main_photo_size_multiplier[1] = True
            case '7':
                print("Enter the output file name: ", end='')
                output_file_name[0] = input()
                output_file_name[1] = True
            case '8':
                print("Enter the output folder: ", end='')
                output_folder[0] = input()
                output_folder[1] = True
            case '9':
                if isReady:
                    if maker is None:
                        maker = MosaicMaker(main_photo_path[0], tile_photos_path[0], tile_size_multiplier[0],
                                            tile_size_ratio[0], epsilon[0], main_photo_size_multiplier[0],
                                            output_file_name[0],
                                            output_folder[0])
                    else:
                        if main_photo_path[1]:
                            maker.setMainPhotoPath(main_photo_path[0])
                            main_photo_path[1] = False
                        if tile_photos_path[1]:
                            maker.setTileFolder(tile_photos_path[0])
                            tile_photos_path[1] = False
                        if tile_size_multiplier[1]:
                            maker.setTileSizeMultiplier(tile_size_multiplier[0])
                            tile_size_multiplier[1] = False
                        if tile_size_ratio[1]:
                            maker.setTileSizeRatio(tile_size_ratio[0])
                            tile_size_ratio[1] = False
                        if epsilon[1]:
                            maker.setEpsilon(epsilon[0])
                            epsilon[1] = False
                        if main_photo_size_multiplier[1]:
                            maker.setMainPhotoSizeMultiplier(main_photo_size_multiplier[0])
                            main_photo_size_multiplier[1] = False
                        if output_file_name[1]:
                            maker.setOutputFileName(output_file_name[0])
                            output_file_name[1] = False
                        if output_folder[1]:
                            maker.setOutputPath(output_folder[0])
                            output_folder[1] = False
                    print("Making mosaic...")
                    maker.create_mosaic()
                else:
                    print("Not all required options are selected!")
            case '10':
                while True:
                    printDatabaseMenu()
                    option = input()
                    match option:
                        case '1':
                            if isReady:
                                name = input("Enter the name of the settings: ")
                                saveSettings(main_photo_path[0], tile_photos_path[0], tile_size_multiplier[0],
                                             tile_size_ratio[0], epsilon[0], main_photo_size_multiplier[0],
                                             output_file_name[0], output_folder[0], name)
                            else:
                                print("Not all required options are selected!")
                        case '2':
                            name = input("Enter the name of the settings you want to load: ")
                            result = loadSettings(name)
                            if result is not None:
                                main_photo_path[0] = result[1]
                                main_photo_path[1] = True
                                tile_photos_path[0] = result[2]
                                tile_photos_path[1] = True
                                tile_size_multiplier[0] = result[3]
                                tile_size_multiplier[1] = True
                                tile_size_ratio[0] = (result[4], result[5])
                                tile_size_ratio[1] = True
                                epsilon[0] = result[6]
                                epsilon[1] = True
                                main_photo_size_multiplier[0] = result[7]
                                main_photo_size_multiplier[1] = True
                                output_file_name[0] = result[8]
                                output_file_name[1] = True
                                output_folder[0] = result[9]
                                output_folder[1] = True
                                isReady = isReadyCheck(main_photo_path, tile_photos_path, tile_size_multiplier,
                                                       tile_size_ratio)
                            else:
                                print("No settings with that id!")
                        case '3':
                            name = input("Enter the name of the settings you want to delete: ")
                            deleteSettings(name)
                        case '4':
                            printSettings()
                        case '5':
                            break
            case '11':
                break
            case _:
                print("Invalid option!")
        print()


class MosaicMaker:

    def __init__(self, main_photo_path, tile_folder_path, tile_size_multiplier, tile_size_ratio, epsilon=0.0,
                 main_photo_size_multiplier=1, output_path=None, output_file_name=None, flip=False):
        self.main_photo_path = main_photo_path
        self.tile_size_multiplier = tile_size_multiplier
        self.tile_size_ratio = tile_size_ratio
        self.tile_size = (tile_size_ratio[0] * tile_size_multiplier, tile_size_ratio[1] * tile_size_multiplier)
        if epsilon is None:
            self.epsilon = 0.0
        else:
            self.epsilon = epsilon
        if main_photo_size_multiplier is None:
            self.size_increase_multiplier = 1
        else:
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
        if flip is None:
            self.flip = False
        else:
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
            # create output folder if it doesn't exist
            if not os.path.exists('output'):
                os.makedirs('output')
            self.final_output_path = '\\'.join(('output', filename))
        else:
            self.final_output_path = '\\'.join((self.output_path, filename))

    def get_tile_list(self):
        tile_paths = []
        for file in glob.glob(self.tile_folder_path):
            if file.__contains__("Summary"):
                continue
            if os.path.isfile(file):
                tile_paths.append(file)
        self.futures = [self.executor.submit(importAndResizeTile, path, self.tile_size, self.is_portrait, self.flip) for
                        path in tile_paths]

    def get_colors(self):
        # Calculate dominant color
        self.tile_list.clear()
        self.colors.clear()
        self.counters.clear()
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
        self.tile_size = (ratio[0] * self.tile_size_multiplier, ratio[1] * self.tile_size_multiplier)
        self.changed = True

    def setTileSizeMultiplier(self, multiplier):
        self.tile_size = (multiplier * self.tile_size_ratio[0], multiplier * self.tile_size_ratio[1])
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
    main()
