import config
import zStackUtils as zsu
import cv2
import math
import numpy as np
import tifffile
import glob
from pathlib import Path
import argparse
import os

# Cropping globals that need to be set at program start
stackDims = None
xProjDims = None

# Cropping globals for cv2 mouse callbacks
refPt = [(0, 0), (0, 0)]
z0 = 0
z1 = 0
XY_CROPPING_WINDOW_LMB_DOWN = False
XY_CROPPING_WINDOW_ACTIVE = False
Z_CROPPING_WINDOW_ACTIVE_LEFT = False
Z_CROPPING_WINDOW_ACTIVE_RIGHT = False


def calc_xy_crop_snap_value(x):

    return int(math.ceil(x / config.XY_CROP_SNAP_INCREMENT)) * int(config.XY_CROP_SNAP_INCREMENT)


def calc_z_crop_snap_value(x):

    return int(math.ceil(x / config.Z_CROP_SNAP_INCREMENT)) * int(config.Z_CROP_SNAP_INCREMENT)


def click_and_crop(event, x, y, flags, param):

    global refPt, XY_CROPPING_WINDOW_ACTIVE, XY_CROPPING_WINDOW_LMB_DOWN, stackDims

    if event == cv2.EVENT_LBUTTONDOWN:
        refPt[0] = refPt[1] = (calc_xy_crop_snap_value(x), calc_xy_crop_snap_value(y))
        XY_CROPPING_WINDOW_ACTIVE = True
        XY_CROPPING_WINDOW_LMB_DOWN = True

    if event == cv2.EVENT_MOUSEMOVE and XY_CROPPING_WINDOW_LMB_DOWN:

        # TODO detect if cropping has gone outside bounds of scan
        x = calc_xy_crop_snap_value(x)
        y = calc_xy_crop_snap_value(y)

        if x > stackDims['x'] or y > stackDims['y']:
            pass
        else:
            refPt[1] = (x, y)

    if event == cv2.EVENT_LBUTTONUP and XY_CROPPING_WINDOW_LMB_DOWN:
        XY_CROPPING_WINDOW_LMB_DOWN = False


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

    XYTextColor = (236, 43, 146)
    XYCropLineColor = (0, 255, 0)
    ZTextColor = (236, 43, 146)
    ZCropLineColor = (0, 255, 0)

    # XY crop conditions not OK
    if refPt[0][0] >= refPt[1][0] or refPt[0][1] >= refPt[1][1]:
        XYTextColor = (0, 0, 255)
        XYCropLineColor = (0, 0, 255)

    # Z crop conditions not OK
    if z0 >= z1:
        ZTextColor = (0, 0, 255)
        ZCropLineColor = (0, 0, 255)

    return [XYTextColor, XYCropLineColor, ZTextColor, ZCropLineColor]


def paint_cropping_text_xy(zProj, colors):


    bg_color = (0, 0, 0)
    bg = np.full((zProj.shape), bg_color, dtype=np.uint8)
    cv2.putText(bg, "xSize=" + str(refPt[1][0] - refPt[0][0]), (40, 110), cv2.FONT_HERSHEY_SIMPLEX, 4.0, colors[0], 8)
    cv2.putText(bg, "ySize=" + str(refPt[1][1] - refPt[0][1]), (40, 110+120), cv2.FONT_HERSHEY_SIMPLEX, 4.0, colors[0], 8)
    x,y,w,h = cv2.boundingRect(bg[:, :, 2])
    zProj[y:y + h, x:x + w] = bg[y:y + h, x:x + w]



def paint_cropping_lines_xy(zProj, colors):

    cv2.rectangle(zProj, refPt[0], refPt[1], colors[1], 8)


def paint_cropping_text_z(xProj, colors):

    cv2.putText(xProj, "zSize=" + str(z1 - z0), (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 2.0, colors[2], 4)


def paint_cropping_line_lmb_z(xProj, colors):

    cv2.line(xProj, (0, z0), (stackDims['x'], z0), colors[3], 2)


def paint_cropping_line_rmb_z(xProj, colors):

    cv2.line(xProj, (0, z1), (stackDims['x'], z1), colors[3], 2)


def paint_cropping_overlays(zProj, xProj, colors):

    if XY_CROPPING_WINDOW_ACTIVE:
        paint_cropping_lines_xy(zProj, colors)
        paint_cropping_text_xy(zProj, colors)

    if Z_CROPPING_WINDOW_ACTIVE_RIGHT:
        paint_cropping_line_rmb_z(xProj, colors)

    if Z_CROPPING_WINDOW_ACTIVE_LEFT:
        paint_cropping_line_lmb_z(xProj, colors)

    if Z_CROPPING_WINDOW_ACTIVE_LEFT and Z_CROPPING_WINDOW_ACTIVE_RIGHT:
        paint_cropping_text_z(xProj, colors)


def crop3D(scanFullPath, cropFullPath, maskFullPath=None):

    global stackDims, xProjDims

    print("\nLoading " + str(scanFullPath))
    scan = tifffile.imread(scanFullPath)
    zProj = zsu.save_and_reload_maxproj(scan)
    xProj = zsu.save_and_reload_maxproj_x(scan)
    yProj = zsu.save_and_reload_maxproj_y(scan)


    # Add mask if supplied
    if maskFullPath != None:

        print("\nLoading " + str(maskFullPath))
        mask = tifffile.imread(maskFullPath)
        zProjMask = zsu.save_and_reload_maxproj(mask)
        yProjMask = zsu.save_and_reload_maxproj_y(mask)
        xProjMask = zsu.save_and_reload_maxproj_x(mask)
        zProj = cv2.addWeighted(zProj, 0.5, zProjMask, 0.5, 0.0)
        yProj = cv2.addWeighted(yProj, 0.5, yProjMask, 0.5, 0.0)
        xProj = cv2.addWeighted(xProj, 0.5, xProjMask, 0.5, 0.0)



    zProjClone = zProj.copy()
    xProjClone = xProj.copy()
    stackDims = zsu.gen_stack_dims_dict(scan)
    stackAspectRatio = stackDims['y'] / stackDims['x']
    xProjDims = dict({'x': xProj.shape[0], 'y': xProj.shape[1]})
    xProjAspectRatio = xProjDims['y'] / xProjDims['x']

    # Cropping config
    CROP_WINDOW_Z_PROJ = "CROP_Z_PROJ"
    CROP_WINDOW_X_PROJ = "CROP_X_PROJ"
    CROP_WINDOW_Y_PROJ = "CROP_Y_PROJ"
    DISPLAY_WIDTH = config.DISPLAY_WIDTH
    DISPLAY_HEIGHT = config.DISPLAY_HEIGHT
    CROP_WINDOW_WIDTH_XY = int(DISPLAY_HEIGHT - 100 * stackAspectRatio)
    CROP_WINDOW_HEIGHT_XY = DISPLAY_HEIGHT - 100
    CROP_WINDOW_WIDTH_Z = DISPLAY_WIDTH - 100
    CROP_WINDOW_HEIGHT_Z = int(DISPLAY_WIDTH - 100 / xProjAspectRatio)



    cv2.namedWindow(CROP_WINDOW_Z_PROJ, cv2.WINDOW_NORMAL)
    cv2.namedWindow(CROP_WINDOW_X_PROJ, cv2.WINDOW_NORMAL)
    cv2.namedWindow(CROP_WINDOW_Y_PROJ, cv2.WINDOW_NORMAL)
    cv2.namedWindow('MASK_Z_PROJ', cv2.WINDOW_NORMAL)
    cv2.namedWindow('MASK_Y_PROJ', cv2.WINDOW_NORMAL)
    cv2.namedWindow('MASK_X_PROJ', cv2.WINDOW_NORMAL)
    cv2.imshow('MASK_Z_PROJ', zProjMask)
    cv2.imshow('MASK_Y_PROJ', yProjMask)
    cv2.imshow('MASK_X_PROJ', xProjMask)

    cv2.setMouseCallback(CROP_WINDOW_Z_PROJ, click_and_crop)
    cv2.setMouseCallback(CROP_WINDOW_X_PROJ, click_and_z_crop)
    print("Cropping " + str(scanFullPath))
    while True:

        # Render the cropping overlays for next frames
        colors = select_cropping_colors()
        paint_cropping_overlays(zProj, xProj, colors)

        # Display the frames with cropping overlays
        cv2.imshow(CROP_WINDOW_Z_PROJ, zProj)
        cv2.imshow(CROP_WINDOW_X_PROJ, xProj)
        cv2.imshow(CROP_WINDOW_Y_PROJ, yProj)

        key = cv2.waitKey(1) & 0xFF

        # Wipe the overlay so next overlay draw has fresh frame
        zProj = zProjClone.copy()
        xProj = xProjClone.copy()

        # Check for user keyboard action
        if key == ord("c"):

            # Check cropping coordinates to make sure they make sense.
            if z0 >= z1:
                print("Z Crop Error: Bottom cannot be above Top. Try again.")
                continue
            elif refPt[0][0] >= refPt[1][0] or refPt[0][1] >= refPt[1][1]:
                print("XY Crop Error: Drag cropping box starting from top-left of desired crop. Try again.")
                continue
            else:
                cv2.destroyAllWindows()
                break

    croppedStack = scan[z0:z1, refPt[0][1]:refPt[1][1], refPt[0][0]:refPt[1][0]]
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
