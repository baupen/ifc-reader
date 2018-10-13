this library converts .ifc format to more readable .json, extracting the 
locations of the specified rooms in there.

install non-standard libraries with `sudo pip install pillow numpy`  

to generate the .json file, run `python ifc_to_json.py IFC_FILE_PATH`  
to generate the graphical preview, run `python json_to_image.py JSON_FILE_PATH`