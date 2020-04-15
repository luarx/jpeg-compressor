![Python 3.7](https://img.shields.io/badge/Python-3.7-blue.svg)

# JPEG COMPRESSOR
Script to reduce the **size of JPEG image files**.

Algorithm source from this Yelp blog:  https://engineeringblog.yelp.com/2017/06/making-photos-smaller.html

How do we achieve this?
--------------------------------------
- **Reducing image quality**:
  - **Fixed** quality chosen by the user.
  - **Dynamic** quality. Selected per image using the **SSIM** algorithm that try to mimic the human vision system to select the best quality where humans will not be able to appreciate the difference between original and modified image.


How to use
------------
- Execute: `pip install -r requirements.txt`
- Look at script options: `python main.py -h`
- Execute it: `python main.py [IMAGES_FOLDER] [--ANOTHER_OPTIONS]`

TIP
-----------
You can create an isolated Python environment to install required libraries with virtualenv:
  - Create a virtualenv: `python -m venv [VENV_FOLDER]`
  - Activate virtualenv: `source [VENV_FOLDER]/bin/activate`


F.A.Q
------------

#### What about original image metadata?

Original image metadata will be copied to the new modified image:
  - **EXIF**. All the original EXIF tags
  - **FILE dates**. Access and modification dates.

#### What happens if I have JPEG images and another image formats in the same folder?

Non-JPEG images will be copied to the destination folder **without being modified**

#### What happens if in the middle of the process there is a failure with one image?

That image will be copied to the `failures` folder so that you can analyze why later
