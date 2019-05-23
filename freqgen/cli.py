from itertools import chain, product

import Bio.Data.CodonTable
import click
import yaml
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from click_default_group import DefaultGroup

from freqgen import amino_acid_seq, codon_frequencies
from freqgen import generate as _generate
from freqgen import k_mer_frequencies
from freqgen import visualize as _visualize


@click.group(cls=DefaultGroup, default="generate", default_if_no_args=True)
def freqgen():
    pass


@freqgen.command(help="Featurize a FASTA file")
@click.argument("filepath", click.Path(exists=True, dir_okay=False))
@click.option(
    "-k",
    multiple=True,
    type=int,
    help="Values of k to featurize the seqs for. May be repeated.",
)
@click.option(
    "-c",
    "--codon-usage",
    is_flag=True,
    help="Whether to include a codon frequency featurization.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(exists=False, dir_okay=False),
    help="The output YAML file.",
)
def featurize(filepath, k, codon_usage, output):
    # get the sequences as strs
    seqs = []
    with open(filepath, "r") as handle:
        for seq in SeqIO.parse(handle, "fasta"):
            seq = str(seq.seq)
            seqs.append(seq)

    if k:
        result = k_mer_frequencies(seqs, k, include_missing=True)
    else:
        result = {}

    # get the codon usage frequencies
    if codon_usage:
        for seq in seqs:
            if len(seq) % 3 != 0:
                raise ValueError(
                    "Cannot calculate codons for sequence whose length is not divisible by 3"
                )
        result["codons"] = codon_frequencies("".join(seqs))

    if output:
        yaml.dump(result, open(output, "w+"), default_flow_style=False)
        return
    print(yaml.dump(result, default_flow_style=False))


@freqgen.command(help="Generate an amino acid sequence from FASTA")
@click.argument("filepath", click.Path(exists=True, dir_okay=False))
@click.option(
    "--mode",
    type=click.Choice(["freq", "seq"]),
    help="Whether to use the exact AA seq or its frequencies. Defaults to freq.",
    default="freq",
)
@click.option(
    "-g",
    "--genetic-code",
    type=int,
    default=11,
    help="The translation table to use. Defaults to 11, the standard genetic code.",
)
@click.option(
    "-l",
    "--length",
    type=int,
    help="The length of the AA sequence (excluding stop codon) to generate if --mode=freq.",
)
@click.option(
    "-s",
    "--stop-codon",
    is_flag=True,
    default=True,
    help="Whether to include a stop codon. Defaults to true.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Whether to print final result if outputting to file. Defaults to false.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(exists=False, dir_okay=False),
    help="The output FASTA file.",
)
def aa(filepath, mode, genetic_code, length, stop_codon, output, verbose):

    # translate the DNA seq, if using exact AA seq
    if mode == "seq":
        try:
            aa_seq = SeqIO.read(filepath, "fasta").seq.translate(table=genetic_code)
        except Bio.Data.CodonTable.TranslationError:
            print(
                "Sequence is not able to be translated! Is it already an amino acid sequence?"
            )
            return
        aa_seq = str(aa_seq).replace("*", "")

    elif mode == "freq":
        # ensure we know how ling the new sequence should be
        if not length:
            print("Must provide lenght parameter using -l INTEGER")
            return

        seqs = []
        # extract the sequences from the reference set
        with open(filepath, "r") as handle:
            for record in SeqIO.parse(handle, "fasta"):
                try:
                    aa_seq = str(
                        record.seq.translate(table=genetic_code)
                    )  # for DNA sequences, translate them
                except Bio.Data.CodonTable.TranslationError:
                    aa_seq = str(
                        record.seq
                    )  # for amino acid sequences, just get the string
                seqs.append(aa_seq)

        # make them into one big sequence
        seqs = "".join(seqs)
        seqs = seqs.replace("*", "")

        # generate a new sequence of the right length
        aa_seq = amino_acid_seq(length, k_mer_frequencies(seqs, 1)[1])

    # add a stop codon, if requested
    if stop_codon:
        aa_seq += "*"

    # output to the file
    if output:
        with open(output, "w+") as output_handle:
            if not isinstance(aa_seq, Seq):
                aa_seq = Seq(aa_seq)
            SeqIO.write(
                SeqRecord(
                    aa_seq,
                    id="Generated by Freqgen from " + str(filepath),
                    description="",
                ),
                output_handle,
                "fasta",
            )

    if verbose or not output:
        print(aa_seq)


@freqgen.command(help="Generate a new DNA sequence with matching features")
@click.option(
    "-s",
    "--original",
    type=click.Path(exists=True, dir_okay=False),
    help="The target amino acid sequence.",
    required=True,
)
@click.option(
    "-t",
    "--target",
    type=click.Path(exists=True, dir_okay=False),
    help="The target frequencies.",
    required=True,
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Whether to show optimization progress. Defaults to false.",
)
@click.option(
    "-i",
    type=int,
    default=50,
    help="How many generations to stop after no improvement. Defaults to 50.",
)
@click.option("-p", type=int, default=100, help="Population size. Defaults to 100.")
@click.option("-m", type=float, default=0.3, help="Mutation rate. Defaults to 0.3.")
@click.option("-c", type=float, default=0.8, help="Crossover rate. Defaults to 0.8.")
@click.option(
    "-r", type=float, default=0, help="Relative improvement threshold. Defaults to 0.0."
)
@click.option(
    "-g",
    "--genetic-code",
    type=int,
    default=11,
    help="The translation table to use. Defaults to 11, the standard genetic code.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(exists=False, dir_okay=False),
    help="The path to the output FASTA file.",
)
@click.option(
    "--mode",
    type=click.Choice(["JSD", "ED"]),
    default="ED",
    help="The fitness function to use. Defaults to Euclidean distance.",
)
def generate(original, target, verbose, i, p, m, c, r, genetic_code, output, mode):
    optimized = _generate(
        yaml.safe_load(open(target)),
        str(SeqIO.read(original, "fasta").seq),
        verbose=verbose,
        max_gens_since_improvement=i,
        population_size=p,
        mutation_probability=m,
        crossover_probability=c,
        genetic_code=genetic_code,
        improvement_rel_threshold=r,
        mode=mode,
    )
    if verbose or not output:
        print(optimized)
    if output:
        with open(output, "w+") as output_handle:
            SeqIO.write(
                SeqRecord(Seq(optimized), id="Optimized by Freqgen", description=""),
                output_handle,
                "fasta",
            )


@freqgen.command(help="Visualize the results of an optimization")
@click.option(
    "-s",
    "--original",
    type=click.Path(exists=True, dir_okay=False),
    help="The original DNA sequence.",
)
@click.option(
    "-t",
    "--target",
    type=click.Path(exists=True, dir_okay=False),
    help="The target frequencies.",
    required=True,
)
@click.option(
    "-r",
    "--optimized",
    type=click.Path(exists=True, dir_okay=False),
    help="The optimized DNA sequence.",
    required=True,
)
@click.option("-l", "--title", type=str, help="The title for the graph.")
@click.option(
    "-w",
    "--width",
    type=int,
    default=1200,
    help="The width of the output graph. Defaults to 1200.",
)
@click.option(
    "-h",
    "--height",
    type=int,
    default=400,
    help="The height of the output graph. Defaults to 400.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(exists=False, dir_okay=False),
    default="freqgen.html",
    help="The path to the output HTML file. Defaults to freqgen.html.",
)
@click.option(
    "--show/--no-show",
    default=True,
    help="Whether to show the resulting visualization file.",
)
@click.option(
    "-g",
    "--genetic-code",
    type=int,
    default=11,
    help="The translation table to use. Defaults to 11, the standard genetic code.",
)
def visualize(
    original, target, optimized, title, width, height, output, show, genetic_code
):
    target = yaml.safe_load(open(target))

    # create a list of the k_mers
    k = sorted((_k for _k in target.keys() if not isinstance(_k, str)))
    k_mers = list(
        chain.from_iterable(
            (("".join(k_mer) for k_mer in product("ACGT", repeat=_k)) for _k in k)
        )
    )

    if "codons" in target.keys() and target.keys():
        k_mers.extend([codon + "*" for codon in sorted(target["codons"].keys())])

    # generate the target vector
    target_vector = []
    for _k in k:
        k_mer_vector = [
            x[1] for x in sorted(list(target[_k].items()), key=lambda x: x[0])
        ]
        target_vector.extend(k_mer_vector)
    if "codons" in target.keys():
        target_vector.extend(
            [x[1] for x in sorted(list(target["codons"].items()), key=lambda x: x[0])]
        )

    seq = SeqIO.read(optimized, "fasta").seq
    if k:
        optimized = list(k_mer_frequencies(seq, k, vector=True))
    else:
        optimized = []
    if "codons" in target.keys():
        optimized.extend(
            [
                x[1]
                for x in sorted(
                    list(codon_frequencies(seq).items()), key=lambda x: x[0]
                )
            ]
        )

    # print(list(zip(optimized, target_vector, k_mers)))
    assert len(optimized) == len(target_vector) == len(k_mers)  # sanity check

    # if the original sequence is given, calculate its k_mer_frequencies
    if original:
        original_seq = SeqIO.read(original, "fasta").seq
        if k:
            original = list(k_mer_frequencies(original_seq, k, vector=True))
        else:
            original = []
        if "codons" in target.keys():
            original.extend(
                [
                    x[1]
                    for x in sorted(
                        list(codon_frequencies(original_seq).items()),
                        key=lambda x: x[0],
                    )
                ]
            )

    if max(k, default=0) >= 3 or "codons" in target.keys():
        click.secho(
            "Displaying a large number of k-mers and/or codons. To view the results of each k-mer, use the zoom tool in the top right of the graph to zoom in or set the width of the graph manually using --width. Suggested width: "
            + str(35 * len(k_mers)),
            fg="yellow",
        )
        click.pause()

    _visualize(
        k_mers,
        target_vector,
        optimized,
        original_freqs=original,
        title=title,
        plot_height=height,
        plot_width=width,
        filepath=output,
        codons="codons" in target.keys(),
        show=show,
    )
