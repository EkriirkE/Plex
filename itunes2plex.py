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
import time
import tempfile

PlexProfileName="Erik"	#Plex profile name to set metadata for, blank/unset for all profiles
#Location of Plex Library database
dbf="Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
#Location of iTunes Music Library XML file
itx="../Music/iTunes Library.xml"
#Match all possible library item matches, otherwise only first match is used
AllMatches=True

#The following are only needed if matching by Library paths+filename
#iTunes Library Location
iTunesLoc="file://localhost/L:/Music/"
#Plex Music Library Location
PlexLoc="/media/Music/"

#Plex SQLite executable, if --direct is passed
SQLite='./"Plex SQLite"'

def eprint(*args,**kwargs):
	print(*args,**kwargs,file=sys.stderr)

direct="--direct" in sys.argv
if not os.path.exists(dbf): raise FileNotFoundError(dbf)
db=sqlite3.connect(dbf)
db.row_factory=sqlite3.Row
db.text_factory=lambda x:x.decode(errors="ignore")
db.isolation_level=None
#Set to shared mode to avoid conflict
db.execute("PRAGMA journal_mode=WAL")
cur=db.cursor()
profiles=[dict(x) for x in db.execute("SELECT id,name FROM accounts").fetchall()]
if PlexProfileName:
	profiles=[next((x for x in profiles if x["name"]==PlexProfileName),dict(id=0))]
	eprint(f"Using {profiles=}")

eprint("Reading "+itx)
xml = ET.parse(itx)
for k in xml.find("dict").findall("key"):
	if k.text != "Tracks": continue
	tracks = k.getnext()

with tempfile.NamedTemporaryFile(mode="w+",delete_on_close=False) if direct else sys.stdout as tmp:
	tmp.write("PRAGMA journal_mode=WAL;\n")
	for t in tracks.findall("key"):
		eprint(".",end="",flush=True)
		d={k.text:k.getnext().text for k in t.getnext().findall("key")}

		q=[]
		f=parse.unquote(d.get("Location","").replace(iTunesLoc,PlexLoc))
		#Try itunes filepath match first
		if f:
			r=db.execute("""SELECT md.guid
					FROM media_parts mp
					INNER JOIN media_items mi ON mi.id=mp.media_item_id
					INNER JOIN metadata_items md ON md.id=mi.metadata_item_id
					WHERE LOWER(file)=LOWER(?)""",(f,)).fetchall()
			if r:
				q+=[x["guid"] for x in r]
				eprint("i",end="",flush=True)
		#Try match on title/artist/album
		if not q or AllMatches:
			r=db.execute("""SELECT ttl.guid,art.guid art_guid,alb.guid alb_guid
					FROM metadata_items ttl
					INNER JOIN metadata_items art ON art.id=ttl.parent_id
					INNER JOIN metadata_items alb ON alb.id=art.parent_id
					WHERE LOWER(ttl.title)=LOWER(?) AND LOWER(art.title)=LOWER(?) AND LOWER(alb.title)=LOWER(?)""",(d.get("Name"),d.get("Artist") or d.get("Genre"),d.get("Album"))).fetchall()
			if r:
				q+=[x["guid"] for x in r if x["guid"] not in q]
				eprint("m",end="",flush=True)
		#Try semi match on title/artist
		if not q or AllMatches:
			r=db.execute("""SELECT ttl.guid,art.guid art_guid
					FROM metadata_items ttl
					INNER JOIN metadata_items art ON art.id=ttl.parent_id
					WHERE LOWER(ttl.title)=LOWER(?) AND LOWER(art.title)=LOWER(?)""",(d.get("Name"),d.get("Artist") or d.get("Genre"))).fetchall()
			if r:
				q+=[x["guid"] for x in r if x["guid"] not in q]
				eprint("s",end="",flush=True)

		#print(d)
		#Set any matching metadata
		for guid in q or []:
			for a in profiles:
				try: pd=time.mktime(time.strptime(d.get("Play Date UTC"),"%Y-%m-%dT%H:%M:%SZ"))
				except: pd=None
				try: da=time.mktime(time.strptime(d.get("Date Added"),"%Y-%m-%dT%H:%M:%SZ"))
				except: da=None
				try: dm=time.mktime(time.strptime(d.get("Date Modified"),"%Y-%m-%dT%H:%M:%SZ"))
				except: dm=None
				pc=int(d.get("Play Count",0))
				rt=int(d.get("Rating",0))/10
				if e:=db.execute("SELECT * FROM metadata_item_settings WHERE account_id=? AND guid=?",(a["id"],guid)).fetchone():
					#Highest viewcount
					if e["view_count"] and pc and e["view_count"]>pc: pc=e["view_count"]
					#Most recent play date
					if e["last_viewed_at"] and pd and e["last_viewed_at"]>pd: pd=e["last_viewed_at"]
					#Earliest creation date
					if e["created_at"] and da and e["created_at"]<da: da=e["created_at"]
					#Most recent modified date
					if e["updated_at"] and dm and e["updated_at"]>dm: dm=e["updated_at"]
					#Average rating
					if e["rating"] and rt: rt=(rt+e["rating"])/2
					q="UPDATE metadata_item_settings SET rating=?,last_viewed_at=?,view_count=?,created_at=?,updated_at=? WHERE account_id=? AND guid=?",(rt,pd,pc,da,dm,a["id"],guid)
				else:
					q="INSERT INTO metadata_item_settings (account_id,guid,rating,view_count,last_viewed_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",(a["id"],guid,rt,pc,pd,da,dm)
					eprint("+",end="",flush=True)
				#Can't execute directly due to Plex customizations
				#db.execute(*q)
				#Convert prepared statement to literal
				sql=q[0].replace(r"?",r"{}").format(*("NULL" if x is None else x if type(x) in (int,float,bool) else "'"+str(x).replace("'","''")+"'" for x in q[1]))
				tmp.write(sql+";\n")
	db.close()
	if direct:	#As a hack we saved everything to a tempfile and tell Plex to read that
		tmp.close()
		eprint("\nUpdating DB")
		os.system(f'{SQLite} "{dbf}" < "{tmp.name}"')
	eprint("Done.")

