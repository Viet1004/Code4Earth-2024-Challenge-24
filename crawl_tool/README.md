# Crawl tool for ECMWF homepage
This script will download publications and reports from ECMWF homepage under pdf format.

## How to use
Direct your working directory to `crawl_tool` folder.
Run the script crawl.py:
`python crawl.py --source memoranda --pages [1,10] --download`

**`--source`**: required. Choose the source to download from among `memoranda`, `report`, `ERA`, `esa-eumetsat`, `eumetsat-ecmwf`.
**`--pages`**: required. Choose which pages to download from. Must be an integer or under the form [start,end].
**`--download`**: activate download mode (default: False). If not activated, the script will not download target files.
**`--verbose`**: activate verbose mode (default: False). If activated, crawled links will be printed on the console.
**`--wait_time`**: wait time between two consecutive file downloads (default: 2 secs). This functionality is included to prevent flooding the server.
**`--output_folder`**: Location to store crawled files (default: `home/user/large-disk/crawled_resources/`).

## Storage

All downloaded files will be stored in `home/user/large-disk/crawled_resources/` folder as default or user's chosen directory.
