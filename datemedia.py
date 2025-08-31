#!/usr/bin/env python
#--------========########========--------
#	PleX Media Server "Added Date" true-up
#	2025-08-31	Erik Johnson - EkriirkE
#
#	Place in the root of the plexmediaserver, where "Plex SQLite" (optionally) and "Library" exists.
#	Run:
#	python datemedia.py
#		 --direct will execute against the DB directly
#
#	SQL output can be >redirected to a file without the status text.
#
#--------========########========--------

import os, sys
import sqlite3
import tempfile

#Optionally use another library location as a timestamp source.  Folder structures must match beyond the root
#	curroot= current lirary root eg "/media/"
#	otherroot= reference library files eg "/mnt/oldplex/" 
curroot=""
otherroot=""
dbf="Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"

#Plex SQLite executable, if --direct is passed
SQLite='./"Plex SQLite"'

def eprint(*args, **kwargs):
	print(*args, **kwargs, file=sys.stderr)

if not os.path.exists(dbf):
	eprint("Database not found!")
	exit(1)
db=sqlite3.connect(dbf)
db.row_factory=sqlite3.Row
db.text_factory=lambda b:b.decode(errors="ignore")
db.isolation_level=None
#Set to shared mode to avoid conflict
db.execute("PRAGMA journal_mode=WAL")

with tempfile.NamedTemporaryFile(mode="w+",delete_on_close=False) as tmp:
	tmp.write("PRAGMA journal_mode=WAL;\n")
	for f in db.execute("""
				SELECT mp.file,md.id mdid, md.added_at,md.created_at md_created_at, mp.created_at mp_created_at,mi.created_at mi_created_at
				FROM metadata_items md
				INNER JOIN media_items mi ON mi.metadata_item_id=md.id
				INNER JOIN media_parts mp ON mp.media_item_id=mi.id
			""").fetchall():
		if not f["file"]: continue
		eprint(".",end="",flush=True)
		try: fd=os.path.getmtime(otherroot+f["file"].removeprefix(curroot))
		except Exception as e:
			eprint(e)
			continue
		fd=int(min(	#Find the smallest timestamp
				fd,
				f["added_at"] or fd,
				f["md_created_at"] or fd,
				f["mp_created_at"] or fd,
				f["mi_created_at"] or fd,
			))
		if fd<(f["added_at"] or fd+1):
			#eprint(f"{f['file']} {fd}<{f['added_at']}")
			sql=f"UPDATE metadata_items SET added_at={fd} WHERE id={f['mdid']};\n"
			#print(sql)
			eprint("\b+",end="",flush=True)
			tmp.write(sql)
			#db.execute(sql)	#Can't execute directly due to PleX customizations
	db.close()
	if len(sys.argv)>1 and sys.argv[1]=="--direct":	#As a hack we saved everything to a tempfile and tell PleX to read that
		tmp.close()
		eprint("\nUpdating DB")
		os.system(f'{SQLite} "{dbf}" < "{tmp.name}"')
	else:
		tmp.seek(0)
		print(tmp.read())
eprint("Done.")
