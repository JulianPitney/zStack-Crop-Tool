import zStackUtils as zsu
import cv2
import math
import numpy as np
import tifffile
import argparse
import os
import sys
import selectinwindow
from win32api import GetSystemMetrics
sys.setrecursionlimit(10 ** 9)


stackDims = None
xProjDims = None

# Cropping globals for cv2 mouse callbacks
z0 = 0
z1 = 0
Z_CROPPING_WINDOW_ACTIVE_LEFT = False
Z_CROPPING_WINDOW_ACTIVE_RIGHT = False


def calc_z_crop_snap_value(x):

    # CROPPING CONFIG
    XY_CROP_SNAP_INCREMENT = float(1.0)
    Z_CROP_SNAP_INCREMENT = float(1.0)
    return int(math.ceil(x / Z_CROP_SNAP_INCREMENT)) * int(Z_CROP_SNAP_INCREMENT)


def click_and_z_crop(event, x, y, flags, param):

    global z0, z1, Z_CROPPING_WINDOW_ACTIVE_RIGHT, Z_CROPPING_WINDOW_ACTIVE_LEFT, xProjDims

    if event == cv2.EVENT_LBUTTONDOWN:

        temp = calc_z_crop_snap_value(y)

        if temp > xProjDims['y']:
            pass
        else:
            Z_CROPPING_WINDOW_ACTIVE_LEFT = True
            z0 = temp

    if event == cv2.EVENT_RBUTTONDOWN:

        temp = calc_z_crop_snap_value(y)

        if temp > xProjDims['y']:

            pass
        else:
            Z_CROPPING_WINDOW_ACTIVE_RIGHT = True
            z1 = temp


def select_cropping_colors():

    ZTextColor = (255, 255, 255)
    ZCropLineColor = (0, 255, 0)

    # Z crop conditions not OK
    if z0 >= z1:
        ZTextColor = (0, 0, 255)
        ZCropLineColor = (0, 0, 255)

    return [ZTextColor, ZCropLineColor]


def paint_cropping_text_z(xyProj, colors):

    bg_color = (0, 0, 0)

    bg = np.full((xyProj.shape), bg_color, dtype=np.uint8)
    cv2.putText(bg, "zSize=" + str(z1 - z0), (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 2.0, colors[0], 4)
    x, y, w, h = cv2.boundingRect(bg[:, :, 2])
    xyProj[y:y + h + 10, x:x + w + 20] = bg[y:y + h + 10, x:x + w + 20]



def paint_cropping_line_lmb_z(xProj, colors, stackDims):

    cv2.line(xProj, (0, z0), (stackDims['x'] + stackDims['y'], z0), colors[1], 2)


def paint_cropping_line_rmb_z(xProj, colors, stackDims):

    cv2.line(xProj, (0, z1), (stackDims['x'] + stackDims['y'], z1), colors[1], 2)


def paint_cropping_overlays(xProj, colors, stackDims):

    if Z_CROPPING_WINDOW_ACTIVE_RIGHT:
        paint_cropping_line_rmb_z(xProj, colors, stackDims)

    if Z_CROPPING_WINDOW_ACTIVE_LEFT:
        paint_cropping_line_lmb_z(xProj, colors, stackDims)

    if Z_CROPPING_WINDOW_ACTIVE_LEFT and Z_CROPPING_WINDOW_ACTIVE_RIGHT:
        paint_cropping_text_z(xProj, colors)


def crop3D(scanFullPath, cropFullPath, maskFullPath=None):

    global stackDims, xProjDims

    print("\nLoading " + str(scanFullPath))
    scan = tifffile.imread(scanFullPath)
    zProj = zsu.save_and_reload_maxproj(scan)
    xProj = zsu.save_and_reload_maxproj_x(scan)
    yProj = zsu.save_and_reload_maxproj_y(scan)
    stackDims = zsu.gen_stack_dims_dict(scan)
    xProjDims = {'x': stackDims['y'], 'y': stackDims['z']}

    # Add mask if supplied
    if maskFullPath != None:

        print("\nLoading " + str(maskFullPath))
        mask = tifffile.imread(maskFullPath)
        zProjMask = zsu.save_and_reload_maxproj(mask)
        yProjMask = zsu.save_and_reload_maxproj_y(mask)
        xProjMask = zsu.save_and_reload_maxproj_x(mask)
        zProjMask = cv2.resize(zProjMask, (stackDims['x'], stackDims['y']), interpolation=cv2.INTER_CUBIC)
        yProjMask = cv2.resize(yProjMask, (stackDims['x'], stackDims['z']), interpolation=cv2.INTER_CUBIC)
        xProjMask = cv2.resize(xProjMask, (stackDims['y'], stackDims['z']), interpolation=cv2.INTER_CUBIC)

        zProj = cv2.addWeighted(zProj, 0.5, zProjMask, 0.5, 0.0)
        yProj = cv2.addWeighted(yProj, 0.5, yProjMask, 0.5, 0.0)
        xProj = cv2.addWeighted(xProj, 0.5, xProjMask, 0.5, 0.0)


    # MERGE X AND Y PROJECTIONS INTO 1 MAT
    xyProjPreAlloc = np.empty((stackDims['z'], stackDims['x'] + stackDims['y'], 3), dtype=np.uint8)
    xyProjPreAlloc[:, 0:stackDims['y'], :] = xProj
    xyProjPreAlloc[:, stackDims['y']:, :] = yProj
    xyProj = xyProjPreAlloc

    bg_color = (0, 0, 0)
    bg = np.full((xyProj.shape), bg_color, dtype=np.uint8)
    cv2.putText(bg, "X Projection", (int(stackDims['x'] / 2) - 500, 50), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4)
    x, y, w, h = cv2.boundingRect(bg[:, :, 2])
    xyProj[y:y + h + 10, x:x + w + 20] = bg[y:y + h + 10, x:x + w + 20]

    bg = np.full((xyProj.shape), bg_color, dtype=np.uint8)
    cv2.putText(bg, "Y Projection", (int(stackDims['x'] + (stackDims['y'] / 2)) - 500, 50), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 4)
    x, y, w, h = cv2.boundingRect(bg[:, :, 2])
    xyProj[y:y + h + 10, x:x + w + 20] = bg[y:y + h + 10, x:x + w + 20]

    xyProjClone = xyProj.copy()


    # Cropping config
    CROP_WINDOW_Z_PROJ = "CROP_Z_PROJ"
    CROP_WINDOW_XY_PROJ = "CROP_XY_PROJ"
    cv2.namedWindow(CROP_WINDOW_XY_PROJ, cv2.WINDOW_NORMAL)
    cv2.moveWindow(CROP_WINDOW_XY_PROJ, 0, 0)
    cv2.resizeWindow(CROP_WINDOW_XY_PROJ,GetSystemMetrics(0), GetSystemMetrics(1))
    cv2.setMouseCallback(CROP_WINDOW_XY_PROJ, click_and_z_crop)
    print("Cropping " + str(scanFullPath))
    while True:

        # Render the cropping overlays for next frames
        colors = select_cropping_colors()
        paint_cropping_overlays(xyProj, colors, stackDims)

        # Display the frames with cropping overlays
        cv2.imshow(CROP_WINDOW_XY_PROJ, xyProj)
        key = cv2.waitKey(1) & 0xFF

        # Wipe the overlay so next overlay draw has fresh frame
        xyProj = xyProjClone.copy()

        # Check for user keyboard action
        if key == ord("c"):

            # Check cropping coordinates to make sure they make sense.
            if z0 >= z1:
                print("Z Crop Error: Bottom cannot be above Top. Try again.")
                continue
            else:
                cv2.destroyWindow(CROP_WINDOW_XY_PROJ)
                break


    # XY Cropping
    rectI = selectinwindow.dragRect
    selectinwindow.init(rectI, zProj, CROP_WINDOW_Z_PROJ, stackDims['x'], stackDims['y'])
    cv2.namedWindow(CROP_WINDOW_Z_PROJ, cv2.WINDOW_NORMAL)
    cv2.moveWindow(CROP_WINDOW_Z_PROJ, 0, 0)
    cv2.resizeWindow(CROP_WINDOW_Z_PROJ,GetSystemMetrics(0), GetSystemMetrics(1))
    cv2.setMouseCallback(CROP_WINDOW_Z_PROJ, selectinwindow.dragrect, rectI)
    cv2.imshow(CROP_WINDOW_Z_PROJ, zProj)
    cv2.waitKey(0)
    x = rectI.outRect.x
    y = rectI.outRect.y
    w = rectI.outRect.w
    h = rectI.outRect.h

    # TODO: Insert draggable ROI box coords here
    croppedStack = scan[z0:z1, y:y+h, x:x+w]
    croppedStackDims = zsu.gen_stack_dims_dict(croppedStack)
    tifffile.imwrite(cropFullPath, croppedStack)
    zsu.print_crop_dims(croppedStackDims)
    return croppedStack


def get_scan_paths(scansDir):

    if not os.path.isdir(scansDir):
        print(scansDir + " does not exist. Exiting.")
        exit()

    scanPaths = os.listdir(path=scansDir)
    for scanPath in scanPaths:
        if os.path.isfile(scansDir + "\\" + scanPath) and scanPath[-4:] == '.tif':
            continue
        else:
            scanPaths.remove(scanPath)

    return scanPaths


# Returns None if no mask directory was provided by CLI interface.
def get_mask_paths(args):

    maskPaths = None

    if 'MASKS_DIR' in args:

        masksDir = args.get('MASKS_DIR')

        if os.path.isdir(masksDir):
            maskPaths = os.listdir(path=masksDir)

            for maskPath in maskPaths:
                if os.path.isfile(masksDir + "\\" + maskPath) and maskPath[-4:] == '.tif':
                    continue
                else:
                    maskPaths.remove(maskPath)


    return maskPaths


def crop_all_stacks(scanPaths, maskPaths, scansDir, args):

    for i in range(0, len(scanPaths)):

        scanFullPath = scansDir + "\\" + scanPaths[i]
        croppedFullPath = scansDir + "\\" + scanPaths[i][:-4] + "_cropped.tif"

        if maskPaths != None:

            masksDir = args.get('MASKS_DIR')
            maskFullPath = masksDir + "\\" + scanPaths[i][:-4] + "_stroke_mask.tif"

            if not os.path.isfile(maskFullPath):
                print("No file was found at " + maskFullPath + " . Exiting.")
                exit(0)
            crop3D(scanFullPath, croppedFullPath, maskFullPath)

        else:
            crop3D(scanFullPath, croppedFullPath)





def main():

    parser = argparse.ArgumentParser(description='This tool allows a user to point to a directory full of tiff stacks and 3DCrop them all one after another.')
    parser.add_argument('--scans_dir', metavar='SCANS_DIR', dest='SCANS_DIR', action='store', required=True, help='Full path to directory where scan tiff stacks are. This directory should ONLY contain scan tiff stacks.')
    parser.add_argument('--masks_dir', metavar='MASKS_DIR', dest='MASKS_DIR', action='store', required=False, help='Full path to directory where stroke masks are. Stroke masks should be 8-bit grayscale tiff st'
                                                                                                                   'acks with the .tif extension. There should be one stroke mask for each scan in the <scans_dir'
                                                                                                                   '> directory and this pairing should have identical ZYX dimensions. The stroke mask .tifs shou'
                                                                                                                   'ld be named following this example: If <scans_dir> has a file called scan1.tif, the corresponding stroke mask'
                                                                                                                   'should be named scan1_stroke_mask.tif')
    args = vars(parser.parse_args())
    scansDir = args.get('SCANS_DIR')
    scanPaths = get_scan_paths(scansDir)
    maskPaths = get_mask_paths(args)
    crop_all_stacks(scanPaths, maskPaths, scansDir, args)






if __name__ == '__main__':
    main()
