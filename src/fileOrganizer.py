# FileOrganizer
# Imports
import csv
import filecmp
import logging
import os
import shutil
import time
import confuse
import json

"""
This script organizes files into separate source folders,
the folder names are created from the file names.
The script will search all files within the 'Source Folder' recursively for any files with matching extensions
to the 'SourceFiles' list.
Version = 2.0.1
"""
"""
This script requires python version 3.9 or above.
To use the script, the user needs to set the following variables in config.yaml file:
    * 'source_folder' - the folder the script will list the files from.
    * 'source_files_ext' - the list of extensions the script will search for,
        you can add more extensions by adding according to the following example.
        '.ext' separated by comma.
    * 'dest_folder' - the destination folder that the script will move the files to, if the 'dest_folder' is empty,
        the script will create the new files under the source_folder.
    * 'log_location' - the folder that the script log will be saved in, if 'log_location' is empty,
        the script will save the log in the 'dest_folder'
    * enable_log = If 'True' the script will write logs, if false the script will not write ANY log. default is 'True'
    * enable_file_log = If 'True' the script will logs to a log file, if false the script will not write the log file.
      default is 'True'
    * enable_console_log = If 'True' the script will logs to console output, if false the script will not write the log.
      default is 'True'
    * generate_csv -If 'True' the script create a csv report of any file change in the following format:
    'Source Folder', 'Source File', 'Destination Folder', 'Destination File'
    * csv_report_name - sets the csv report name.
"""

# ----------------------------------------------------------------------------------------------------------------
# Global Variables
# ----------------------------------------------------------------------------------------------------------------

# Application Name
AppName = 'FileOrganizer'

# Configure how many times to run script for timing \\ DO NOT MODIFY THIS VALUE!
RUNS = 1

# ----------------------------------------------------------------------------------------------------------------
# DO NOT MODIFY THE SCRIPT BEYOND THIS POINT
# ----------------------------------------------------------------------------------------------------------------


# Configuration function
# Read Configuration file
def read_config_yaml():

    # set configuration file settings
    config = confuse.Configuration(AppName)  #Application Name
    config.set_file('./config.yaml')         #Configuration File location
    
    # Parse configuration file
    # Set global variables
    global source_folder, dest_folder, log_location, source_files_ext, \
        recursive, enable_log, log_level, enable_file_log, enable_console_log, \
        generate_csv, csv_report_name
    # parse config file into variables
    source_folder = config['Folders']['source_folder'].get(confuse.STRING)
    dest_folder = config['Folders']['destination_folder'].get(confuse.STRING)
    log_location = config['Folders']['log_location'].get(confuse.STRING)
    source_files_ext = config['Files']['source_files_ext'].as_str_seq()
    recursive = config['Other']['recursive'].get()
    enable_log = config['Logs']['enable_log'].get()
    log_level = config['Logs']['log_level'].get()
    enable_file_log = config['Logs']['enable_file_log'].get()
    enable_console_log = config['Logs']['enable_console_log'].get()
    generate_csv = config['Logs']['generate_csv'].get()
    csv_report_name = config['Logs']['csv_report_name'].get(confuse.STRING)
    

def read_config():

    # set configuration file settings
    config = './config.json'        #Configuration File location
    config = json.load(config)     #Load configuration file

    # parse config file into variables
    source_folder = config["Folders"]["source_folder"]
    dest_folder = config['Folders']['destination_folder']
    log_location = config['Folders']['log_location']
    source_files_ext = config['Files']['source_files_ext']
    recursive = config['Other']['recursive']
    enable_log = config['Logs']['enable_log']
    log_level = config['Logs']['log_level']
    enable_file_log = config['Logs']['enable_file_log']
    enable_console_log = config['Logs']['enable_console_log']
    generate_csv = config['Logs']['generate_csv']
    csv_report_name = config['Logs']['csv_report_name']

# logger function
# creates logger handler
def config_logger():

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create file handler and set level to debug
    fh = logging.FileHandler(filename=os.path.join(log_location, AppName +'.log'), encoding='utf-8')
    fh.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')

    # add formatter to ch and fh
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    # add ch and fh to logger
    if enable_console_log:
        logger.addHandler(ch)
    if enable_file_log:
        logger.addHandler(fh)
    
    # sets file logging level, accepts: debug, error, info
    if log_level.upper() == 'INFO':
        logger.setLevel(logging.INFO)
    elif log_level.upper() == 'DEBUG':
        logger.setLevel(logging.DEBUG)
    elif log_level.upper() == 'ERROR':
        logger.setLevel(logging.ERROR) 
    elif log_level.upper() == 'WARNING':
        logger.setLevel(logging.WARNING)
    else:
        print('log level was not set, please configure log level as one of these options\n'
        'INFO,WARNING,ERROR,DEBUG')
        exit(1)


# function dir_scanner
# input: source Folder to scan, source File extensions to search
# returns 2 object lists: sub folder list and files list
def dir_scanner(source_folder, source_files_ext):
    logger.debug('dir_scanner - initiating [sub_folders] and [files] lists')
    sub_folders, files = [], []                                                # init lists of sub_folders and files
    for entry in os.scandir(source_folder):                                    # itirate the first folder
        if os.path.isdir(entry.path):                                              # check if entry is folder
            sub_folders.append(entry)                                          # add entry to sub_folders list
            logger.debug('found sub folder: %s in folder [%s]', entry.name, os.path.dirname(entry.path))
        if os.path.isfile(entry.path):                                             # check if enrty is file
            if os.path.splitext(entry.name)[1].lower() in source_files_ext:                # check if entry has the right extensions
                files.append(entry)                                           # add entry to files list
                logger.info('found file: [%s] in folder [%s]', entry.name, os.path.dirname(entry.path))
    if recursive:                                                             # check if to search recursively
        for source_folder in list(sub_folders):                                 # recursive check in all sub_folders
            r_sub_folders, r_files = dir_scanner(source_folder, source_files_ext)     # do recursion function
            sub_folders.extend(r_sub_folders)                                   # extend new sub_folders to list
            files.extend(r_files)                                             # append sub_file to list
    return sub_folders, files                                                  # return sub_folders and files lists


# function create_folder
# input: destination folder to move the files to, the list of files created by dir_scanner function
# must run dir_scanner first
# returns an object list of created folders
def create_folder(dest_folder, list_files):
    created_folder = []                                                        # init list of created folders
    for folder in list_files:                                                 # iterate through list of files
        file_name = os.path.splitext(folder.name)                             # save file name without extension
        dest_folder_name = (os.path.join(dest_folder, file_name[0]))            # save destination folder name
        logger.debug('folder: [%s] created', dest_folder_name)
        try:
            os.mkdir(dest_folder_name)                                         # create destination folder
        except FileExistsError:                                               # handle folder exists error
            logger.warning('[%s] folder already exists', dest_folder_name)
            pass
        except Exception as err:                                              # log other errors
            logger.warning('error returned: ([%s]) ', err)
            raise
        created_folder.append(dest_folder_name)                                 # add created folder object to list
    return created_folder                                                      # return a list of creted folders


def move_files(dest_folder_name, list_files):
    for file in list_files:
        dest_folder_full = os.path.join(dest_folder_name, os.path.splitext(file.name)[0])
        dest_file_full = os.path.join(dest_folder_full, file.name)
        if os.path.exists(dest_file_full):
            if compare_file(file.path, dest_file_full):
                try:
                    shutil.move(file.path, os.path.join(dest_folder_full, file.name))
                except OSError as err:
                    logger.error('[%s]', err)
                    raise
                logger.warning('[%s] already exists in folder [%s], and its contents is matching the source file, '
                               'file will be replaced', file.name, dest_folder_full)
        
                if generate_csv:
                    f = open(os.path.join(log_location, csv_report_name), "a")
                    print(file.path + "," + file.name + "," + dest_folder_full + "," + file.name, file=f)
                    f.close()

            else:
                file_new_name = os.path.splitext(file.name)[0] + '_copy' + os.path.splitext(file.name)[1]
                try:
                    shutil.move(file.path, os.path.join(dest_folder_full, file_new_name))
                except OSError as err:
                    logger.error('[%s]', err)
                    raise
                logger.warning('[%s] already exists in folder [%s], and its contents does not match the '
                                'source file, ''file will be created as a copy', file.name, dest_folder_full)
                if generate_csv:
                    f = open(os.path.join(log_location, csv_report_name), "a")
                    print(file.path + "," + file.name + "," + dest_folder_full + "," + file_new_name, file=f)
                    f.close()

        else:
            try:
                shutil.move(file.path, os.path.join(dest_folder_full, file.name))
                logger.info('[%s] did not exist in folder [%s], moving file', file.name, dest_folder_full)
                if generate_csv:
                    f = open(os.path.join(log_location, csv_report_name), "a")
                    print(file.path + "," + file.name + "," + dest_folder_full + "," + file.name, file=f)
                    f.close()
            except OSError as err:
                logger.error('[%s]', err)
                raise


def delete_empty_folders(sub_folders_list):
    deleted_folder = []
    for folder in sub_folders_list:
        if not os.listdir(folder):
            logger.info('[%s] is empty, will delete it', folder.path)
            try:
                os.rmdir(folder)
                deleted_folder.append(folder)
            except OSError as err:
                logger.error('[%s]', err)
    return deleted_folder

def compare_file(file, dest_file_full):
    return filecmp.cmp(file, dest_file_full)


if __name__ == '__main__':

    read_config()
    # create logger
    logger = logging.getLogger(AppName)

    if enable_log:
        config_logger()
    logger.info('-------------------------------------------------------------------------------------------------')
    logger.info('START OF SCRIPT')
    logger.info('-------------------------------------------------------------------------------------------------\n')

    # Sanity checks
    logger.debug('CHECK - checking if source_folder is set')
    if source_folder == '':
        logger.error('CHECK - Source Folder must be configured for the script to run, exists script')
        exit(1)
    else:
        logger.debug('CHECK - source_folder is set to: [%s]', source_folder)
    logger.debug('CHECK - checking if dest_folder is set')
    if dest_folder == '':
        logger.warning('CHECK - Destination Folder was not configured, using source folder')
        dest_folder = source_folder
    else:
        logger.debug('CHECK - dest_folder is set to: [%s]', dest_folder)
    logger.debug('CHECK - checking if log_location is set')
    if log_location == '':
        logger.warning('Log location Folder was not configured, using destination folder')
        log_location = dest_folder
    else:
        logger.debug('CHECK - log_location is set to: [%s]', log_location)
    logger.debug('CHECK - checking if generate_csv is set')
    if generate_csv:
        try:
            f = open(os.path.join(log_location, csv_report_name), "w")
            logger.debug('CHECK - generate_csv is set to: [%s]', os.path.join(log_location, csv_report_name))
        except OSError as e:
            logger.error('CHECK - [%s]', e, "setting generate_csv to false")
            generate_csv = False
        if generate_csv:
            f = open(os.path.join(log_location, csv_report_name), "w")
            f.write("Source Folder, Source File, Destination Folder, Destination File")
            f.write("\n")
            f.close()
            logger.debug('CHECK - created csv file [%s]', os.path.join(log_location, csv_report_name))

    # start scan
    logger.debug('Time - Setting start time of actual script')
    start_time = time.time_ns()
    logger.debug('RUN - running script functions')
    for i in range(RUNS):
        logger.info('listing files found in source folder: [%s]', source_folder)
        list_sub_folders, list_files = dir_scanner(source_folder, source_files_ext)
        logger.info('creating folders in destination folder: [%s]', dest_folder)
        created_folder = create_folder(dest_folder, list_files)
        logger.info('moving files from source folder to destination folder')
        move_files(dest_folder, list_files)
        logger.info('deleting empty folders in source folder')
        deleted_folder = delete_empty_folders(list_sub_folders)
    logger.debug('Time - Setting end time of actual script')
    end_time = time.time_ns()
    logger.debug('Time - calculating run time')
    total_time = end_time - start_time
    logger.info(f'script ran for:[{total_time / 1000 / 1000 / RUNS:.0f}ms]')
    logger.info('-------------------------------------------------------------------------------------------------')
    logger.info('END OF SCRIPT')
    logger.info('-------------------------------------------------------------------------------------------------\n')
