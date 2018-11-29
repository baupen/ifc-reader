import os
import glob
import ifc_to_json
import json
import hashlib


def is_ifc_file(file_path):
    return file_path.split(".")[-1] == "ifc"


def does_json_exist(ifc_file_path, files_in_folder):
    query = ifc_file_path + '.json'
    return query in files_in_folder


def get_data_hash_from_ifc(ifc_file_path):
    with open(ifc_file_path, 'r') as ifc_file_handle:
        return hashlib.sha256(ifc_file_handle.read().encode('utf-8')).hexdigest()


def get_json_content(json_file_path):
    with open(json_file_path, 'rb') as json_file:
        return json.load(json_file)


def add_hash(ifc_file_path):
    """
    it is assumed that the corresponding JSON has the name of the IFC file but with a '.json' appended
    """
    json_content = get_json_content(ifc_file_path + ".json")
    json_content['hash'] = get_data_hash_from_ifc(ifc_file_path)

    with open(ifc_path + ".json", 'w', encoding="utf8") as outfile:
        json.dump(json_content, outfile, ensure_ascii=False, indent=4)


def data_hash_same(ifc_file_path):
    ifc_data_hash = get_data_hash_from_ifc(ifc_file_path)
    json_data_hash = get_json_content(ifc_file_path+".json")["hash"]
    return ifc_data_hash == json_data_hash


if __name__ == '__main__':
    construction_sites_folder = "construction_sites/"
    folders = [construction_sites_folder + name for name in os.listdir(construction_sites_folder)]
    for folder in folders:
        files = glob.glob(folder + "/maps/*")
        ifc_files = filter(lambda path: is_ifc_file(path), files)
        for ifc_file in ifc_files:
            if does_json_exist(ifc_file, files) and data_hash_same(ifc_file):
                continue
            ifc_to_json.run_conversion(ifc_file)
