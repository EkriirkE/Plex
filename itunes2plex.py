#!/usr/bin/env python
#--------========########========--------
#	iTunes Mulic Library.xml ratings to Plex Media Server
#	2025-09-25	Erik Johnson - EkriirkE
#
#	Place in the root of the plexmediaserver, where "Plex SQLite" (optionally) and "Library" exists.
#	Run:
#	python datemedia.py
#		 --direct will execute against the DB directly
#
#	SQL output can be >redirected to a file without the status text.
#
#--------========########========--------

from lxml import etree as ET
import os, sys
import sqlite3
from urllib import parse

PlexAcctName="Erik"	#Plex account name to set metadata for, blank/unset for all accounts
#Location of Plex Library database
dbf="Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
#Location of iTunes Music Library XML file
itx="../Music/iTunes Library.xml"

def eprint(*args,**kwargs):
	print(*args,**kwargs,file=sys.stderr)

if not os.path.exists(dbf): raise FileNotFoundError(dbf)
db=sqlite3.connect(dbf)
db.row_factory=sqlite3.Row
db.text_factory=lambda x:x.decode(errors="ignore")
db.isolation_level=None
#Set to shared mode to avoid conflict
db.execute("PRAGMA journal_mode=WAL")
cur=db.cursor()
accountid=[dict(x) for x in db.execute("SELECT id,name FROM accounts").fetchall()]
if PlexAcctName:
	accountid=[next((x for x in accountid if x["name"]==PlexAcctName),dict(id=0))]
	eprint(f"Using account {accountid}")

xml = ET.parse(itx)
for k in xml.find("dict").findall("key"):
	if k.text != "Tracks": continue
	tracks = k.getnext()
	
for t in tracks.findall("key"):
	eprint(".",end="",flush=True)
	d={k.text:k.getnext().text for k in t.getnext().findall("key")}

	q=None
	f=parse.unquote(d.get("Location","").replace("file://localhost/L:/Music/","/media/Music/")).replace("iTunes Media/Music/","")
	#Try exact filename match first
	if f:
		q=db.execute("""SELECT md.guid
				FROM media_parts mp
				INNER JOIN media_items mi ON mi.id=mp.media_item_id
				INNER JOIN metadata_items md ON md.id=mi.metadata_item_id
				WHERE LOWER(file)=LOWER(?)""",(f,)).fetchall()
		if q: eprint("\bi",end="",flush=True)
	#Try match on title/artist/album
	if not q:
		q=db.execute("""SELECT ttl.guid,art.guid art_guid,alb.guid alb_guid
				FROM metadata_items ttl
				INNER JOIN metadata_items art ON art.id=ttl.parent_id
				INNER JOIN metadata_items alb ON alb.id=art.parent_id
				WHERE LOWER(ttl.title)=LOWER(?) AND LOWER(art.title)=LOWER(?) AND LOWER(alb.title)=LOWER(?)""",(d.get("Name"),d.get("Artist") or d.get("Genre"),d.get("Album"))).fetchall()
		if q: eprint("\bm",end="",flush=True)
	#Try match on title/artist
	if not q:
		q=db.execute("""SELECT ttl.guid,art.guid art_guid
				FROM metadata_items ttl
				INNER JOIN metadata_items art ON art.id=ttl.parent_id
				WHERE LOWER(ttl.title)=LOWER(?) AND LOWER(art.title)=LOWER(?)""",(d.get("Name"),d.get("Artist") or d.get("Genre"))).fetchall()
		if q: eprint("\bs",end="",flush=True)

	#print(d)
	#Set any matching metadata
	for r in q or []:
		for a in accountid:
			if db.execute("SELECT * FROM metadata_item_settings WHERE account_id=? AND guid=?",(a["id"],r["guid"])).fetchone():
				q="UPDATE metadata_item_settings SET rating=?,last_viewed_at=max(last_viewed_at,?),view_count=max(view_count,?) WHERE account_id=? AND guid=?",(int(d.get("Rating",0))/10,d.get("Play Date",0),d.get("Play Count",0),a["id"],r["guid"])
			else:
				q="INSERT INTO metadata_item_settings (account_id,guid,rating,view_count,last_viewed_at) VALUES (?,?,?,?,?)",(a["id"],r["guid"],int(d.get("Rating",0))/10,d.get("Play Count",0),d.get("Play Date"))
			#Can't execute directly due to Plex customizations
			#db.execute(*q)
			#Convert prepared statement to literal for copy/paste
			print(q[0].replace(r"?",r"{}").format(*("NULL" if x is None else x if type(x) in (int,float,bool) else "'"+str(x).replace("'","''")+"'" for x in q[1])))

db.close()
eprint("\nDone.")