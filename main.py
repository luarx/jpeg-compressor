#!/usr/bin/env python

# SOURCE https://engineeringblog.yelp.com/2017/06/making-photos-smaller.html
# Exif data https://orthallelous.wordpress.com/2015/04/19/extracting-date-and-time-from-images-with-python/
# piexif fix https://github.com/hMatoba/Piexif/issues/95

from PIL import Image

from io import StringIO
import PIL.Image
from ssim import compute_ssim
from math import log
import piexif

import traceback
import os
# shutil is consisting of high-level Python specific functions. shutil is on top of Python `os module`.
# Thus, we can use the shutil module for high-level operations on files.
# For example: Use it to copy files and metadata
import shutil

import argparse


def get_ssim_at_quality(photo, quality):
    """Return the ssim for this JPEG image saved at the specified quality"""
    ssim_photo = "ssim_photo.jpg"
    # optimize is omitted here as it doesn't affect
    # quality but requires additional memory and cpu
    photo.save(ssim_photo, format="JPEG", quality=quality, progressive=True)
    ssim_score = compute_ssim(photo, PIL.Image.open(ssim_photo))

    # Remove temporal photo which is using to calculate the ssim
    os.remove(ssim_photo)

    return ssim_score


def _ssim_iteration_count(lo, hi):
    """Return the depth of the binary search tree for this range"""
    if lo >= hi:
        return 0
    else:
        return int(log(hi - lo, 2)) + 1


def jpeg_dynamic_quality(original_photo):
    """Return an integer representing the quality that this JPEG image should be
    saved at to attain the quality threshold specified for this photo class.

    Args:
        original_photo - a prepared PIL JPEG image (only JPEG is supported)
    """
    ssim_goal = 0.95
    hi = 85
    lo = 80

    # working on a smaller size image doesn't give worse results but is faster
    # changing this value requires updating the calculated thresholds
    photo = original_photo.resize((400, 400))

    # if not _should_use_dynamic_quality():
    #     default_ssim = get_ssim_at_quality(photo, hi)
    #     return hi, default_ssim

    # 95 is the highest useful value for JPEG. Higher values cause different behavior
    # Used to establish the image's intrinsic ssim without encoder artifacts
    normalized_ssim = get_ssim_at_quality(photo, 95)
    selected_quality = selected_ssim = None

    # loop bisection. ssim function increases monotonically so this will converge
    for i in range(_ssim_iteration_count(lo, hi)):
        curr_quality = (lo + hi) // 2
        curr_ssim = get_ssim_at_quality(photo, curr_quality)
        ssim_ratio = curr_ssim / normalized_ssim

        if ssim_ratio >= ssim_goal:
            # continue to check whether a lower quality level also exceeds the goal
            selected_quality = curr_quality
            selected_ssim = curr_ssim
            hi = curr_quality
        else:
            lo = curr_quality

    if selected_quality:
        return selected_quality, selected_ssim
    else:
        default_ssim = get_ssim_at_quality(photo, hi)
        return hi, default_ssim


def reduce_jpeg_size_and_save(image, image_destination_path, quality: None):
    # load exif data
    exif_dict = piexif.load(image.info["exif"])
    try:
        # Drop this tag if exists because PIEXIF library has a bug with the format
        # "dump" got wrong type of exif value.\n41729 in Exif IFD. Got as <class \'int\'>.
        # See bug https://github.com/hMatoba/Piexif/issues/95
        del exif_dict['Exif'][piexif.ExifIFD.SceneType]
    except:
        pass
    exif_bytes = piexif.dump(exif_dict)

    # Use dynamic quality if it is not specified
    if not quality:
        # Get the dynamic quality to apply
        (quality, ssim) = jpeg_dynamic_quality(image)

    print(f'Selected quality: {quality} - SSIM: {ssim}')

    save_args = {}
    save_args['quality'] = quality
    save_args['optimize'] = True
    # Preserve EXIF information (dates...)
    save_args['exif'] = exif_bytes
    image.save(f"{image_destination_path}", **save_args)


def preserve_file_dates(source_file, destination_file):
    """
    Preserve original FILE dates.
    There are also EXIF dates that they are already being preserved
    """

    stat = os.stat(source_file)
    # Preserve access and modification date FILE attributes (EXIF are other dates)
    os.utime(destination_file, (stat.st_atime, stat.st_mtime))


if __name__ == '__main__':
    """
    What does is script does:
    1. NON-JPEG Images are copied to the destination folder without being modified
    2. JPEG images:
      2.1 Reduce image Quality
        2.1.1 Use a fixed quality if defined or a dynamic one
        2.1.2 Preserve EXIF metadata (dates, conditions...)
      2.2 Preserve FILE metadata (dates...)
    3. Invalid image files are copied to failures folder
    """

    # INPUT arguments
    ###
    parser = argparse.ArgumentParser(description='Compress JPEG files size')
    # Source folder is mandatory
    parser.add_argument('source_folder',
                        help='images source folder')
    parser.add_argument('--destination_folder',
                        help='images destination folder. Default is `source_folder/results`')
    parser.add_argument('--failures_folder',
                        help='images destination folder. Default is `destination_folder/failures`')
    parser.add_argument('--quality',
                        type=int,
                        choices=range(1, 95),
                        help='image quality between 1-95. Default is best DYNAMIC option`')

    args = parser.parse_args()

    source_folder = args.source_folder
    destination_folder = args.destination_folder or f'{source_folder}/results'
    failures_folder = args.failures_folder or f'{destination_folder}/failures'
    quality = args.quality
    #
    ###

    # Destination folder. Create if does not exist
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # Process images
    with os.scandir(source_folder) as entries:
        for entry in entries:
            if entry.is_file():
                try:

                    print(entry.name)

                    image_source_path = f'{source_folder}/{entry.name}'
                    image_destination_path = f'{destination_folder}/{entry.name}'

                    image = Image.open(image_source_path)

                    if image.format == 'JPEG':
                        reduce_jpeg_size_and_save(image=image,
                                                  image_destination_path=image_destination_path,
                                                  quality=quality)

                        preserve_file_dates(source_file=image_source_path,
                                            destination_file=image_destination_path)
                    else:
                        print(f'Image format is not JPEG (will not be reduced): {image.format}')
                        # This method is like shutil.copy2 but it also try to preserves the file’s metadata (including dates)
                        shutil.copy2(image_source_path, image_destination_path)

                except Exception as exception:
                    # Create failures folder if it does not exist
                    if not os.path.exists(failures_folder):
                        os.makedirs(failures_folder)

                    image_failure_path = f'{failures_folder}/{entry.name}'
                    # Copy files that have raised an exception to the failure folder
                    shutil.copy2(image_source_path, image_failure_path)

                    # Show exception stack trace
                    traceback.print_exc()
