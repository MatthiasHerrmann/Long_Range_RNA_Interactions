import pandas as pd
import os
from Bio import SeqIO

def read_out_bed6_data(file):
    f = open(file, "r")
    UTR5len, CDSlen, UTR3len = None, None, None
    lines = f.readlines()
    if len(lines) == 3: ## Filter files without UTR data
        UTR5end = lines[0].split("\t")[2]
        CDSend = lines[1].split("\t")[2]
        UTR3end = lines[2].split("\t")[2]
        UTR5len = int(UTR5end)
        CDSlen = int(CDSend) - int(UTR5end)
        UTR3len = int(UTR3end) - int(CDSend)
    return UTR5len, CDSlen, UTR3len


def write_static_parameters(static_d, output):
    """Writes a file with all the parameters,
    that should be the same for all IntaRNA processes.
    """
    df = pd.DataFrame(static_d)
    df.to_csv(output)

def create_parameter_table(database_path, extra_bases, output):
    """Scans a given directory for .bed6 files and extracts their information
    """
    d = {}
    for root, dirs, files in os.walk(database_path):
        for file in files:
            if file.endswith(".bed6"):
                # This split will only work with a database built like the given..
                vclass, vtype, virus = root.split("/")[-3:]
                split_name = file.split(".")[:-1]
                vid = ".".join(split_name)
                UTR5len, CDSlen, UTR3len = read_out_bed6_data(f"{root}/{file}")
                if UTR5len is None: # File had no UTR data
                    continue
                DNA = SeqIO.read(f"{root}/{vid}.fa", "fasta")
                # Taking "[0]" will cause issues should we ever get .fa
                # files with more than 1 sequence (shouldnt happen I think?)
                seq5 = str(DNA.seq[:UTR5len+extra_bases])
                seq3 = str(DNA.seq[-UTR3len-extra_bases:])
                d[vid] = [vclass, vtype, virus, UTR5len, CDSlen, UTR3len, seq5, seq3]

    columns = ["class", "type", "virus", "UTR5len", "CDSlen", "UTR3len", "seq5", "seq3"]
    df = pd.DataFrame(d)
    df.index = pd.Index(columns, name="id")
    df = df.T
    df.to_csv(output, index_label="id")
