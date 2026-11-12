"""Restore a real session ZIP into a fresh isolated home, then verify native history.

Uses trusted local runtime schemas. Does not modify an existing Codex home.
The restored directory is retained so evidence and referenced assets stay available.
"""
import argparse
import json
from pathlib import Path
import session_transfer as transfer
from session_clone import AppServer


def verify(args):
    archive = Path(args.zip).resolve()
    z,m,records,_ = transfer.read_bundle(archive,args.max_bytes)
    z.close()
    with transfer.isolated_destination(args.folder,args.schema_home) as home:
        project = home.parent/(home.name+'-project')
        options = argparse.Namespace(zip=str(archive),session_id=m['session_id'],codex_home=str(home),
            project_root=str(project),map=[],identity_map=args.identity_map,apply=True,
            offline_confirmed=True,conflict='abort',max_bytes=args.max_bytes,allow_incomplete=False)
        imported = transfer.import_session(options)
        # Check every imported selected row is present before starting a runtime.
        row_counts = {}
        for name,data in records.items():
            with transfer.ro_db(home/name) as db:
                for table,rows in data.items():
                    count=db.execute('SELECT count(*) FROM '+transfer.ident(table)).fetchone()[0]
                    if count != len(rows):
                        raise ValueError('Restored row count mismatch: '+name+'/'+table)
                    row_counts[name+'/'+table]=count
        for entry in m['files']:
            target=transfer.contained(home if entry['area']=='codex' else project,entry['path'])
            if entry['kind']=='binary' and transfer.file_sha(target)!=entry['sha256']:
                raise ValueError('Restored binary asset differs: '+entry['path'])
    # No app-server is active during the isolated import exemption above.
    with AppServer(args.codex_binary,home,timeout=60) as client:
        native = client.verify(m['session_id'])
    result={'status':'verified_isolated_restore','session_id':m['session_id'],
        'archive':str(archive),'archive_sha256':transfer.file_sha(archive),'codex_home':str(home),
        'project_root':str(project),'session_count':len(m['session_ids']),
        'file_count':len(m['files']),'database_rows':row_counts,'native':native,
        'import_result':imported,'ui_visibility':'Not verified; native API checked'}
    transfer.journal_write(home/'session-transfer'/'verification.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip',required=True)
    parser.add_argument('--folder',required=True)
    parser.add_argument('--schema-home',required=True)
    parser.add_argument('--codex-binary',required=True)
    parser.add_argument('--identity-map',action='append',default=[])
    parser.add_argument('--max-bytes',type=int,default=2*1024**3)
    print(json.dumps(verify(parser.parse_args()),ensure_ascii=False,indent=2))
