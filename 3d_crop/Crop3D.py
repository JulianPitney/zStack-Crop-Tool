import config
import zStackUtils as zsu
import cv2
import math
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

    cv2.putText(zProj, "xSize=" + str(refPt[1][0] - refPt[0][0]), (40, 110), cv2.FONT_HERSHEY_SIMPLEX, 4.0, colors[0], 8)
    cv2.putText(zProj, "ySize=" + str(refPt[1][1] - refPt[0][1]), (40, 110+120), cv2.FONT_HERSHEY_SIMPLEX, 4.0, colors[0], 8)


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


def crop3D(STACK_FULL_PATH, destDir):

    global stackDims, xProjDims

    print("\nLoading " + str(STACK_FULL_PATH))
    stack = tifffile.imread(STACK_FULL_PATH)
    print("Cropping " + str(STACK_FULL_PATH))
    zProj = zsu.save_and_reload_maxproj(stack)
    xProj = zsu.save_and_reload_maxproj_x(stack)
    yProj = zsu.save_and_reload_maxproj_y(stack)
    zProjClone = zProj.copy()
    xProjClone = xProj.copy()

    stackDims = zsu.gen_stack_dims_dict(stack)
    stackAspectRatio = stackDims['y'] / stackDims['x']
    xProjDims = dict({'x': xProj.shape[0], 'y': xProj.shape[1]})
    xProjAspectRatio = xProjDims['y'] / xProjDims['x']

    # Cropping config
    CROP_WINDOW_NAME_XY = "3D Crop Utility XY"
    CROP_WINDOW_NAME_Z = "3D Crop Utility Z"
    CROP_WINDOW_NAME_YPROJ = "Y Projection"
    DISPLAY_WIDTH = config.DISPLAY_WIDTH
    DISPLAY_HEIGHT = config.DISPLAY_HEIGHT
    CROP_WINDOW_WIDTH_XY = int(DISPLAY_HEIGHT - 100 * stackAspectRatio)
    CROP_WINDOW_HEIGHT_XY = DISPLAY_HEIGHT - 100
    CROP_WINDOW_WIDTH_Z = DISPLAY_WIDTH - 100
    CROP_WINDOW_HEIGHT_Z = int(DISPLAY_WIDTH - 100 / xProjAspectRatio)



    cv2.namedWindow(CROP_WINDOW_NAME_XY, cv2.WINDOW_NORMAL)
    cv2.namedWindow(CROP_WINDOW_NAME_Z, cv2.WINDOW_NORMAL)
    cv2.namedWindow(CROP_WINDOW_NAME_YPROJ, cv2.WINDOW_NORMAL)

    cv2.setMouseCallback(CROP_WINDOW_NAME_XY, click_and_crop)
    cv2.setMouseCallback(CROP_WINDOW_NAME_Z, click_and_z_crop)

    while True:

        # Render the cropping overlays for next frames
        colors = select_cropping_colors()
        paint_cropping_overlays(zProj, xProj, colors)

        # Display the frames with cropping overlays
        cv2.imshow(CROP_WINDOW_NAME_XY, zProj)
        cv2.imshow(CROP_WINDOW_NAME_Z, xProj)
        cv2.imshow(CROP_WINDOW_NAME_YPROJ, yProj)
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

    croppedStack = stack[z0:z1, refPt[0][1]:refPt[1][1], refPt[0][0]:refPt[1][0]]
    croppedStackDims = zsu.gen_stack_dims_dict(croppedStack)
    tifffile.imwrite(destDir, croppedStack)
    zsu.print_crop_dims(croppedStackDims)
    return croppedStack


def main():

    parser = argparse.ArgumentParser(description='Parse a directory path pointing to some tif stacks.')
    parser.add_argument('--tiffs_dir', metavar='TIFFS_DIR', dest='TIFFS_DIR', action='store', required=True, help='Full path to directory where tiff stacks are. This directory should ONLY contain tiff stacks.')
    args = vars(parser.parse_args())

    TIFFS_DIR = args.get('TIFFS_DIR')
    if not os.path.isdir(TIFFS_DIR):
        print(TIFFS_DIR + " does not exist. Exiting.")

    stacks = os.listdir(path=TIFFS_DIR)
    for stack in stacks:
        if os.path.isfile(TIFFS_DIR + "\\" + stack) and stack[-4:] == '.tif':
            continue
        else:
            print(TIFFS_DIR + "\\" + stack + " does not exist or does not have the .tif extension. Skipping file.")
            stacks.remove(stack)

    for stack in stacks:

        stackFullPath = TIFFS_DIR + "\\" + stack
        croppedFullPath = TIFFS_DIR + "\\" + stack[:-4] + "_cropped.tif"
        crop3D(stackFullPath, croppedFullPath)

    print("All stacks cropped! Have a wonderful day.")


if __name__ == '__main__':
    main()
