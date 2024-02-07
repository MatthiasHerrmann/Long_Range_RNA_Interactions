import os
import sys
import subprocess
import ast
#from Codes.MRRI import MRRIHandler
import Codes.MRRI_main

def run_command(cmd):
    p = subprocess.run(cmd.split(" "))


def find_all(s, c):
    """Generator that finds and returns the locations 
    of all characters c in a string s.
    """
    idx = s.find(c)
    while idx != -1:
        yield idx
        idx = s.find(c, idx + 1)


def integrate_into(s1, s2, l):
    ##s1 = ..AA..AA
    ##s2 = ....CC..
    pos = find_all(s2, l)
    for i in pos:
        s1 = s1[:i] + l + s1[i+1:]
    return s1


def run_mlocarna(input_fasta, output_dir, use_carna=False):
    """Run mlocarna on a given fasta file.
    
    input_fasta (str): Filepath to a fasta file to apply locarna on
    output_dir (str): Filepath of the resulting CM file
    """
    
    if use_carna:
        print(f"mlocarna(+carna): {input_fasta} `=> {output_dir}")
        ## Doesnt work: :(
        #carna_loc = subprocess.Popen(["conda", "run", "-n", "carna", "which", "carna"], stdout=subprocess.PIPE)
        #carna_loc.wait()
        #print(carna_loc)
        #raise
        carna_loc = "/home/arkanini/miniconda3/envs/carna/bin/carna"
        cmd = ["conda", "run", "-n", "carna"]
    else:
        print(f"mlocarna: {input_fasta} `=> {output_dir}")
        cmd = ["conda", "run", "-n", "locarna"]
    cmd += ["mlocarna", input_fasta,
           #"--indel=-50", # Webserver parameter
           #"--indel-opening=-750", # Webserver parameter
           "--width=300",
           "--use-ribosum=true",
           #"--pw-aligner=$(which carna)",
           "--tgtdir", output_dir
           ]
    if use_carna:
        cmd += [f"--pw-aligner={carna_loc}"]
    print(" ".join(cmd))
    raise
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    p.wait()


def run_rnaalifold(input_dir):
    print(f"RNAalifold : {input_dir}/result.aln => {input_dir}/alirna.ps+aln.ps")
    input_file = f"{input_dir}/result.aln"
    with open(input_file, "r") as f:
        for line in f.readlines():
            if line.startswith("#A1"):
                anchor_seq = line.split(" ")[-1]
                s1, s2 = anchor_seq.split("BBBBBBB")
                constraint = b"."+b"<"*(len(s1)-1) + b"xxxxxxx" + b">"*(len(s2)-1)
                break
    cmd = ["RNAalifold", input_file,
           "--aln", "--ribosum_scoring",
           "--cfactor", "0.6",
           "--nfactor", "0.5",
           "--color", "-C"
           ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    p.communicate(input=constraint)
    p.wait()
    os.rename("alirna.ps", f"{input_dir}/alirna.ps")
    os.rename("aln.ps", f"{input_dir}/aln.ps")


def run_ps_to_pdf(ps_file, output):
    print(f"ps2pdf: {ps_file} `=> {output}")
    cmd = ["ps2pdf", "-dEPSCrop", ps_file, output]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    p.wait()

def hacked_MRRI_main(UTR5pCDS, UTR3pCDS, static_param_path, param_mode):
    sys.argv = ["Codes/MRRI_main.py", "-q", UTR3pCDS, "-t", UTR5pCDS, "-p", static_param_path]
    MRRIHandler = Codes.MRRI_main.main()
    for qId in MRRIHandler.querySeq.keys():
        for tId in MRRIHandler.targetSeq.keys():
            BE = dict({ 'id1': tId, 'id2' : qId})
            B1 = MRRIHandler.runIntaRNA(BE, param_mode)
            #print(B1)
            if "id2" in B1:
                B2 = MRRIHandler.runIntaRNA(B1, param_mode)
            else:
                BErr = {"start1":0, "end1":0, "start2":0, "end2":0, "hybridDP":0}
                return [BErr] ## First IntaRNA round didnt find anything
            #print(B2)
            if "id2" in B2:
                B3 = MRRIHandler.runIntaRNA(B2, param_mode)
            else:
                return [B1]
            #print(B3)
            if "id2" in B3:
                return [B1, B2, B3]
            else:
                return [B1, B2]


def run_mrri(UTR5pCDS, UTR3pCDS, static_param_path):
    """Outdated. Currently not in use"""
    cmd = ["python", "Codes/MRRI_main.py", "-q", UTR3pCDS, "-t", UTR5pCDS, "-p", static_param_path]
    #print(" ".join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    p.wait()
    stdout = list(p.stdout)[0].decode("utf-8")
    d = ast.literal_eval(stdout)
    return stdout, d