# PleX
PleX Media Server Scripts

Stop the plexmediaserver service before making midifications to the database.

While in the plexmediaserver folder, where the program `Plex SQLite` lives....

### datemedia.py
Update the "Date Added" in PleX to match the modification date of the source media - only if it is older.  
Sometimes reorganizing your media folders causes PleX to detect (old) media as a new addition and sort it accordingly.  
If the file is newer that the original added date and it get updated, the best you can with this script is to "touch" the media file(s) with the expected dates before running this script.


### Move library location, and its contents, from `/media/OldPath` to `/media/NewLocation`
```sqlite
UPDATE section_locations SET root_path='/media/NewLocation' WHERE root_path='/media/OldPath';
UPDATE media_parts SET file=REPLACE(file,'/media/OldPath/','/media/NewLocation/') WHERE file LIKE '/media/OldPath/%';
```
