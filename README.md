# Plex
Plex Media Server Scripts

Stop the plexmediaserver service and back up the database files before making modifications.

While in the plexmediaserver folder, where the program `Plex SQLite` lives....

### datemedia.py
Update the "Date Added" in Plex to match the modification date of the source media - only if it is older.  
Sometimes reorganizing your media folders causes Plex to detect (old) media as a new addition and sort it accordingly.  I don't like old media showing up in recommended as "new".  
If the file is newer that the original added date and it get updated, the best you can with this script is to "touch" the media file(s) with the expected dates before running this script.  
Protip:  An in-place file replacement is usually ignored by Plex, so avoid moving or renaming old media if replacing it with a better copy (of the exact same name and extension).  

---

### Manual SQL stuff

Enter the Plex SQL Environment via
```shell
./Plex\ SQLite "Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
```

#### Move library location, and its contents, from `/media/OldPath` to `/media/NewLocation`
```sql
-- Library location
UPDATE section_locations SET root_path='/media/NewLocation' WHERE root_path='/media/OldPath';
-- Library contents' locations
UPDATE media_parts SET file=REPLACE(file,'/media/OldPath/','/media/NewLocation/') WHERE file LIKE '/media/OldPath/%';
```
