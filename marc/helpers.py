#!/usr/bin/env python

import argparse
import glob
from itertools import cycle

import networkx as nx
import numpy as np

from marc.exceptions import InputError
from marc.molecule import Molecule


def yesno(question):
    """Simple Yes/No Function."""
    prompt = f"{question} ? (y/n): "
    ans = input(prompt).strip().lower()
    if ans not in ["y", "n"]:
        print(f"{ans} is invalid, please try again...")
        return yesno(question)
    if ans == "y":
        return True
    return False


def bround(x, base: float = 10, type=None) -> float:
    if type == "max":
        return base * np.ceil(x / base)
    elif type == "min":
        return base * np.floor(x / base)
    else:
        tick = base * np.round(x / base)
        return tick


def chunker(seq, size):
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))


def group_data_points(bc, ec, names):
    try:
        groups = np.array([str(i)[bc:ec].upper() for i in names], dtype=object)
    except Exception as m:
        raise InputError(
            f"Grouping by name characters did not work. Error message was:\n {m}"
        )
    type_tags = np.unique(groups)
    cycol = cycle("bgrcmky")
    cymar = cycle("^ospXDvH")
    cdict = dict(zip(type_tags, cycol))
    mdict = dict(zip(type_tags, cymar))
    cb = np.array([cdict[i] for i in groups])
    ms = np.array([mdict[i] for i in groups])
    return cb, ms


def molecules_from_file(filename, noh=True):
    molecules = []
    f = open(filename, "r")
    n_atoms = 0

    lines = list(f.readlines())
    f.close()
    try:
        n_atoms = int(lines[0].strip())
    except ValueError:
        raise InputError(
            f"Could not obtain the number of atoms in the .xyz file {filename} from first line. Check format."
        )

    if len(lines) % (n_atoms + 2) != 0:
        raise InputError(
            f"Could not parse trajectory xyz file {filename} properly. Check format."
        )
    for chunk in chunker(lines, n_atoms + 2):
        molecule = Molecule(lines=chunk, noh=noh)
        molecules.append(molecule)
    return molecules


def processargs(arguments):

    mbuilder = argparse.ArgumentParser(
        prog="marc",
        description="Analyse conformer ensembles to find the most representative structures.",
        epilog="Remember to cite the marc paper or repository - \n if they have a DOI by now\n - and enjoy!",
    )
    mbuilder.add_argument(
        "-version", "--version", action="version", version="%(prog)s 1.0"
    )
    runmode_arg = mbuilder.add_mutually_exclusive_group()
    mbuilder.add_argument(
        "-i",
        "--i",
        "-input",
        dest="input",
        nargs="?",
        action="append",
        type=str,
        required=True,
        help="Filename(s) containing the conformational ensemble as an xyz trajectory, or separately as xyz files.",
    )
    mbuilder.add_argument(
        "-c",
        "--c",
        "-cluster",
        "--cluster",
        dest="c",
        type=str,
        default="kmeans",
        help="Clustering algorithms to use. (default: kmeans)",
    )
    mbuilder.add_argument(
        "-m",
        "--m",
        "-metric",
        "--metric",
        dest="m",
        type=str,
        default="ewrmsd",
        help="Metric to use to define distance. (default: ewrmsd)",
    )
    mbuilder.add_argument(
        "-v",
        "--v",
        "--verb",
        dest="verb",
        type=int,
        default=0,
        help="Verbosity level of the code. Higher is more verbose and viceversa. (default: 1)",
    )
    mbuilder.add_argument(
        "-pm",
        "--pm",
        "-plotmode",
        "--plotmode",
        dest="plotmode",
        type=int,
        default=1,
        help="Plotting mode. Higher is more detailed, lower is more basic. (default: 1)",
    )
    args = mbuilder.parse_args(arguments)

    if len(args.input) > 1:
        filenames = args.input
        terminations = [i[-3:] for i in filenames]
        if not all(terminations == "xyz"):
            raise InputError(
                f"Files with {terminations} instead of all xyz termination fed as input. Exiting."
            )
        molecules = [Molecule(filename=i) for i in filenames]

    elif len(args.input) == 0:
        filenames = glob.glob("./*.xyz")
        terminations = [i[-3:] for i in filenames]
        if not all(terminations == "xyz"):
            raise InputError(
                f"Files with {terminations} instead of all xyz termination fed as input. Exiting."
            )
        molecules = [Molecule(filename=i) for i in filenames]

    else:
        termination = args.input[0][-3:]
        if termination == "xyz":
            molecules = molecules_from_file(args.input[0])
        else:
            raise InputError(
                f"File with {termination} instead of xyz termination fed as input. Exiting."
            )

    if args.c not in ["kmeans", "dbscan"]:
        raise InputError("Unknown clustering strategy selected. Exiting.")

    if args.m not in ["rmsd", "erel", "da", "ewrmsd", "ewda", "mix"]:
        raise InputError("Unknown metric for clustering selected. Exiting.")

    return (
        molecules,
        args.c,
        args.m,
        args.plotmode,
        args.verb,
    )


def test_molecules_from_file(path="marc/test_files/"):
    filenames = [
        "3_h2o_conformers.xyz",
    ]
    for filename in filenames:
        molecules = molecules_from_file(f"{path}{filename}", noh=False)
        for molecule in molecules:
            print(molecule.energy, molecule.coordinates, molecule.atoms)
            assert molecule.energy is not None
