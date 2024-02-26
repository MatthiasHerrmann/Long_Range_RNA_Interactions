import os
import sys
import subprocess
import ast
import math
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
    """
    s1 = "..AA..AA"
    s2 = "....CC.."
    l  = "C"
    res= "..AACCAA"
    """
    pos = find_all(s2, l)
    for i in pos:
        s1 = s1[:i] + l + s1[i+1:]
    return s1


def add_cm_hit_to_fs(fs, cmhit, cmstart):
    """
    fs    = "AAAAAA.NNN..a.aa.aaa......."
    cmhit = "<<-<->->>"
    cmstart= 8
    # Insert into our fs string
    result= "AAAAAA.NNN..a.aa.a<<-<->->>"
    # Replace replaced letters on the opposing site with "."
    result= "..AAAA.NNN..a.aa.a<<-<->->>"
    ..Should be good enough to replace the first n occurences of that letter?
    """
    from collection import Counter
    counts = Counter(fs[cmhit:]) # Count occurences of each letter thats being replaced
    for letter, amount in counts:
        if letter == ".":
            continue
        fs.replace(letter.upper(), ".", amount)
    return fs

def cm_compare(id, seq, cm_file):
    """- Open alignment file where the CMhit is from
    - find right sequence
    - read sequence from input and compare with cmhit
    - if match, insert respective part from cmhit
    - if not, shift cmhit sequence to the next base
    """
    #print(id)
    location = None
    result_string = ""
    name_found = False
    with open(cm_file, "r") as f:
        for line in f.readlines():
            if (not name_found) and line.startswith("#=GS") and line.split()[3] == id:
                name, location = line.split()[1].split("/")
                name_found = True
                #print(name, location)
            elif name_found and line.startswith(name):
                cm_seq = line.split()[1]
                cm_seq = cm_seq.upper().replace("U", "T")
            elif line.startswith("#=GC SS_cons"):
                align_cons = line.split()[-1]
            #elif id == "NC_018705.3":
            #    print(line)
    #print("AAAAAAAAAA")
    if not location:
        print(f"No CM alignment found for {id}")
        return None
    else:
        location_start, location_end = location.split("-")
        cut_seq = seq[int(location_start)+199:]
        cut_seq_pos = 0
        for i in range(len(cm_seq)):
            if cm_seq[i] == cut_seq[cut_seq_pos]:
                result_string += align_cons[i]
                cut_seq_pos += 1
        return result_string


def run_mlocarna(input_fasta, output_dir, use_carna=False):
    """Run mlocarna on a given fasta file.
    
    input_fasta (str): Filepath to a fasta file to apply locarna on
    output_dir (str): Filepath of the resulting CM file
    """
    
    if use_carna:
        print(f"mlocarna(+carna): {input_fasta} `=> {output_dir}")
        ## Doesnt work: :(
        conda_base = subprocess.Popen(["conda", "info", "--base"], stdout=subprocess.PIPE)
        conda_base.wait()
        carna_loc = list(conda_base.stdout)[0].decode("utf-8").rstrip("\n")
        carna_loc += "/envs/carna/bin/carna"
        #carna_loc = "/home/arkanini/miniconda3/envs/carna/bin/carna"
        cmd = ["conda", "run", "-n", "carna"]
    else:
        print(f"mlocarna: {input_fasta} `=> {output_dir}")
        cmd = ["conda", "run", "-n", "locarna"]
    cmd += ["mlocarna", input_fasta,
           #"--indel=-50", # Webserver parameter
           #"--indel-opening=-750", # Webserver parameter
           "--width=3000",
           "--use-ribosum=true",
           "--tgtdir", output_dir
           ]
    if use_carna:
        cmd += [f"--pw-aligner={carna_loc}"]
    #print(" ".join(cmd))
    #raise
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    p.wait()


def run_consensus_constraint(locARNA_input, locARNA_output):
    cmd = ["conda", "run", "-n", "r-tidyverse"]
    cmd += ["Rscript", "--vanilla", "Codes/consensus-constraint.R",
            "-a", locARNA_output,
            "-c", locARNA_input]
    print(" ".join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    p.wait()
    consensus_constraint = list(p.stdout)[0].decode("utf-8")
    return consensus_constraint


def get_modified_s_cons_for_seq(seq_dir_list, locarna_alignment_seq, mode):
    seq = seq_dir_list[0] + "NNNNNNN" + seq_dir_list[1]
    seq = seq.replace("T", "U")
    filler = "."
    if mode == 2:
        filler = "x"
    current_pos = 0
    reached_end = False
    result = ""
    for base in locarna_alignment_seq:
        if (not reached_end) and base == seq[current_pos]:
            result += seq_dir_list[2][current_pos]
            current_pos += 1
            reached_end = current_pos >= len(seq)
        else:
            result += filler
    return result


def run_rnaalifold(locARNA_output_dir, seq_dir_entries, mode=0, locARNA_input=""):
    """
    locARNA_output_dir(str): Directory location of the locARNA result to look at
    seq_dir_entries(list): list of seq_dir entries corrosponding to the locARNA_output_dir, 
                           [(id, part5, part3, cons_S, cons_1, cons_2, cons_FS), (), ...]
    mode(int): Mode for the S constraints used
               0: Empty S constraint                              ( ....xxxxxxx.... )
               1: Left/Right separated                            ( <<<<xxxxxxx>>>> )
               2: Blocked except for CMHit                        ( xxxxxxxxxxxx... )
               3: Consensus constraint of locARNA FS interactions ( .((.xxxxxxx.).) )
    locARNA_input(str): Directory of file that was used as the input for locARNA. Only needed for mode 3
    """
    print(f"RNAalifold : {locARNA_output_dir}/result.aln => {locARNA_output_dir}/alirna.ps+aln.ps")
    locARNA_output = f"{locARNA_output_dir}/result.aln"
    seq_dir_entry_dict = {}
    for i in seq_dir_entries:
        seq_dir_entry_dict[i[0]] = i[1:]
    with open(locARNA_output, "r") as f:
        for line in f.readlines():
            split_line = line.split()
            #print(split_line)
            if ((mode == 2 or mode == 3) and
                len(split_line) == 2 and split_line[0] != "#A1"):
                new_s_cons = get_modified_s_cons_for_seq(seq_dir_entry_dict[split_line[0]], split_line[1], mode)
                seq_dir_entry_dict[split_line[0]].append(new_s_cons)
            if line.startswith("#A1"):
                anchor_seq = line.split()[-1]
                s1, s2 = anchor_seq.split("BBBBBBB")
                if mode == 0:
                    constraint = "."*len(s1) + "xxxxxxx" + "."*(len(s2)-1)
                elif mode == 1:
                    constraint = "<"*len(s1) + "xxxxxxx" + ">"*(len(s2)-1)
                elif mode == 2:
                    earliest_pos = math.inf
                    for key, value in seq_dir_entry_dict.items():
                        group = key.split("-")[0]
                        if group in locARNA_output_dir:
                            cons = value[-1]
                            cm_pos = cons.find(".")
                            if cm_pos < earliest_pos:
                                earliest_pos = cm_pos
                    constraint = "x"*earliest_pos + "."*(len(s1)+7+len(s2)-1-earliest_pos)
                elif mode == 3:
                    constraint = run_consensus_constraint(locARNA_input, locARNA_output)
                else:
                    raise ValueError("Invalid mode for #S constraint")
                break
    cmd = ["RNAalifold", locARNA_output,
           "--aln", "--ribosum_scoring",
           "--cfactor", "0.6",
           "--nfactor", "0.5",
           "--color", "-C" # -C is constraint
           ]
    #print(" ".join(cmd))
    #print(constraint)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    p.communicate(input=str.encode(constraint))
    p.wait()
    os.rename("alirna.ps", f"{locARNA_output_dir}/alirna.ps")
    os.rename("aln.ps", f"{locARNA_output_dir}/aln.ps")


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
