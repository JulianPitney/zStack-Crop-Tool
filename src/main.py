import zStackUtils as zsu
import Crop3D
import DensityMap3D
import config
import tifffile
import glob
from pathlib import Path
import cv2

def crop_scans_dir():

    STACK_PATHS = glob.glob(config.SCANS_DIR + "*.tif")
    CROPPED_DIR = Path(config.SCANS_DIR + 'cropped\\')
    CROPPED_DIR.mkdir(parents=False, exist_ok=False)

    for stackPath in STACK_PATHS:
        temp = Path(stackPath)
        stem = temp.stem
        croppedPath = str(CROPPED_DIR) + "\\" +stem + "_cropped.tif"
        Crop3D.crop3D(stackPath, croppedPath)

    print("All scans cropped! Have a wonderful day.")

def crop_and_cubify_scans_dir():

    STACK_PATHS = glob.glob(config.SCANS_DIR + "*.tif")
    DENSITY_MAPS_DIR = Path(config.SCANS_DIR + 'density_maps\\')
    DENSITY_MAPS_DIR.mkdir(parents=False, exist_ok=False)
    CROPPED_DIR = Path(config.SCANS_DIR + 'cropped\\')
    CROPPED_DIR.mkdir(parents=False, exist_ok=False)
    CUBES_PATHS = []
    AIVIA_RESULTS_PATHS = []
    for path in STACK_PATHS:
        temp = Path(path)
        stem = temp.stem
        cubesPath = Path(config.SCANS_DIR + stem + "_cubes\\")
        excelPath = Path(config.SCANS_DIR + stem + "_excel\\")

        try:
            Path(cubesPath).mkdir(parents=False, exist_ok=False)
            Path(excelPath).mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            print("FileExistsError. Directory creation failed.")
        except FileNotFoundError:
            print("FileNotFoundError. Directory creation failed.")
        except:
            print("UnknownError. Directory creation failed.")
        else:
            CUBES_PATHS.append(str(cubesPath) + "\\")
            AIVIA_RESULTS_PATHS.append(str(excelPath) + "\\")


    for stackPath, cubesOutput in zip(STACK_PATHS, CUBES_PATHS):

        temp = Path(stackPath)
        stem = temp.stem
        croppedPath = str(CROPPED_DIR) + "\\" +stem + "_cropped.tif"

        cropped = Crop3D.crop3D(stackPath, croppedPath)
        cubes = DensityMap3D.slice_into_cubes(cropped, config.CUBE_DIM_Z, config.CUBE_DIM_Y, config.CUBE_DIM_X)
        DensityMap3D.save_cubes_to_tif(cubes, cubesOutput)


def wait_for_aivia():

    input("Program is pausing to wait for Aivia results. When all the cubes "
          "directories have been run through Aivia, and all the excel directories "
          "have results in them, press enter to generate density maps...")



def gen_density_maps_from_aivia_results():

    STACK_PATHS = glob.glob(config.SCANS_DIR + "*.tif")
    CROPPED_PATHS = []
    CROPPED_DIR = Path(config.SCANS_DIR + 'cropped\\')
    DENSITY_MAPS_DIR = Path(config.SCANS_DIR + 'density_maps\\')
    AIVIA_RESULTS_PATHS = []

    for path in STACK_PATHS:

        temp = Path(path)
        stem = temp.stem
        excelPath = Path(config.SCANS_DIR + stem + "_excel\\")
        AIVIA_RESULTS_PATHS.append(str(excelPath) + "\\")
        CROPPED_PATHS.append(str(CROPPED_DIR) + "\\" +stem + "_cropped.tif")


    i = 0

    # GENERATE DENSITY MAPS
    for excelResPath, stackPath in zip(AIVIA_RESULTS_PATHS, STACK_PATHS):

        print("genning " + str(stackPath))
        cubes = DensityMap3D.load_aivia_excel_results_into_cubes(excelResPath)
        DensityMap3D.map_path_lengths_to_range(cubes)
        stack = tifffile.imread(CROPPED_PATHS[i])
        i+=1
        temp = Path(stackPath)
        stem = temp.stem

        for cube in cubes:
            stack[cube.original_z_range[0]:cube.original_z_range[1],
            cube.original_y_range[0]:cube.original_y_range[1],
            cube.original_x_range[0]:cube.original_x_range[1]] = cube.totalPathLength

        max = zsu.max_project(stack)
        cv2.imwrite(str(DENSITY_MAPS_DIR) + "\\" + str(stem) + '_densityMap.png', max)




crop_scans_dir()
#crop_and_cubify_scans_dir()
#gen_density_maps_from_aivia_results()

