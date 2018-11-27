from freqgen import generate


def test_1mer():
    assert generate({1: dict(A=0.5, T=0.5, G=0, C=0)}, "FK") == "TTTAAA"


def test_codon():
    targets = dict(codons={'AAA': 0,
                           'AAC': 0,
                           'AAG': 0,
                           'AAT': 0,
                           'ACA': 0,
                           'ACC': 1 / 3,
                           'ACG': 0,
                           'ACT': 1 / 3,
                           'AGA': 0,
                           'AGC': 0,
                           'AGG': 0,
                           'AGT': 0,
                           'ATA': 0,
                           'ATC': 0,
                           'ATG': 0,
                           'ATT': 0,
                           'CAA': 0,
                           'CAC': 0,
                           'CAG': 0,
                           'CAT': 0,
                           'CCA': 0,
                           'CCC': 0,
                           'CCG': 0,
                           'CCT': 0,
                           'CGA': 0,
                           'CGC': 0,
                           'CGG': 0,
                           'CGT': 0,
                           'CTA': 0,
                           'CTC': 0,
                           'CTG': 0,
                           'CTT': 0,
                           'GAA': 0,
                           'GAC': 0,
                           'GAG': 0,
                           'GAT': 0,
                           'GCA': 0,
                           'GCC': 0,
                           'GCG': 0,
                           'GCT': 0,
                           'GGA': 0,
                           'GGC': 0,
                           'GGG': 0,
                           'GGT': 0,
                           'GTA': 0,
                           'GTC': 0,
                           'GTG': 0,
                           'GTT': 0,
                           'TAA': 0,
                           'TAC': 0,
                           'TAG': 1 / 3,
                           'TAT': 0,
                           'TCA': 0,
                           'TCC': 0,
                           'TCG': 0,
                           'TCT': 0,
                           'TGA': 0,
                           'TGC': 0,
                           'TGG': 0,
                           'TGT': 0,
                           'TTA': 0,
                           'TTC': 0,
                           'TTG': 0,
                           'TTT': 0})
    assert generate(targets, "TT*") in ["ACTACCTAG", "ACCACTTAG"]
