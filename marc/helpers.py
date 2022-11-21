#!/usr/bin/env python

import argparse
import glob
import re
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
        default="mix",
        help="Metric to use to define distance. (default: mix)",
    )
    mbuilder.add_argument(
        "-n",
        "--n",
        "--n_clusters",
        dest="n",
        default=None,
        help="Number of representative conformers to select. (default: select using gap method)",
    )
    mbuilder.add_argument(
        "-ewin",
        "--ewin",
        dest="ewin",
        default=None,
        help="If set to a float, energy window for conformers to be accepted. (default: None)",
    )
    mbuilder.add_argument(
        "-efile",
        "--efile",
        dest="efile",
        default=None,
        help="If set to a filename, file containing the energies of each conformer in crest format. (default: None)",
    )
    mbuilder.add_argument(
        "-v",
        "--v",
        "--verb",
        dest="verb",
        type=int,
        default=1,
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
        basename = filenames[0].split("/")[-1].split(".")[0]
        if not all(terminations == "xyz"):
            raise InputError(
                f"Files with {terminations} instead of all xyz termination fed as input. Exiting."
            )
        molecules = [Molecule(filename=i) for i in filenames]

    # This is left as a hook, but should basically never trigger due to argparse
    elif len(args.input) == 0:
        filenames = glob.glob("./*.xyz")
        terminations = [i[-3:] for i in filenames]
        basename = filenames[0].split("/")[-1].split(".")[0]
        if not all(terminations == "xyz"):
            raise InputError(
                f"Files with {terminations} instead of all xyz termination fed as input. Exiting."
            )
        molecules = [Molecule(filename=i) for i in filenames]

    else:
        basename = args.input[0].split("/")[-1].split(".")[0]
        termination = args.input[0][-3:]
        if termination == "xyz":
            molecules = molecules_from_file(args.input[0])
        else:
            raise InputError(
                f"File with {termination} instead of xyz termination fed as input. Exiting."
            )
    # Set energy window if requested
    if args.ewin is not None:
        try:
            ewin = float(args.ewin)
        except TypeError:
            raise InputError(
                f"ewin was set to {args.ewin} which is not a float nor None. Exiting."
            )
    else:
        ewin = None

    # Set energy file if provided
    if args.efile is not None:
        try:
            filename = str(args.efile)
        except TypeError:
            raise InputError(
                f"efile was set to {args.efile} which is not a string nor None. Exiting."
            )
        try:
            energies = []
            g = open(filename, "r")
            _RE_COMBINE_WHITESPACE = re.compile(r"\s+")
            for line in g.readlines():
                trline = _RE_COMBINE_WHITESPACE.sub(" ", line).strip()
                e = float(trline.split(" ")[1])
                energies.append(e)
            g.close()
        except OSError:
            raise InputError(
                f"efile was set to {filename} which could not be found or opened to read energies. Exiting."
            )
        except TypeError:
            raise InputError(
                f"Line \n{line}\n did not satisfy the expected crest-like format. Exiting."
            )
        # Setting up energies in molecule objects
        if args.verb > 0:
            print(
                "Setting up energies from file. This will overwrite the energy values in the xyz files. Double check the ordering!"
            )
        if len(molecules) == len(energies):
            for i, (molecule, energy) in enumerate(zip(molecules, energies)):
                molecule.energy = energy
                if args.verb > 1:
                    print(f"Molecule {i} set with energy {energy}")
        else:
            raise InputError(
                f"The number of molecules ({len(molecules)}) and energies ({len(energies)}) in file {filename} does not match. Exiting."
            )

    # Check for atom ordering and number
    sort = False
    for molecule_a, molecule_b in zip(molecules, molecules[1:]):
        atoms_a = molecule_a.atoms
        atoms_b = molecule_b.atoms
        if len(atoms_a) == len(atoms_b):
            if not all(atoms_a == atoms_b):
                sort = True
        else:
            raise InputError("Molecules do not have the same number of atoms. Exiting.")
        natoms = len(atoms_b)
        if natoms == 1:
            raise InputError("Molecules are monoatomic. Exiting.")
        elif natoms == 2:
            dof = 1
        else:
            dof = 3 * len(atoms_b) - 6
        if not dof > 0:
            raise InputError("Molecules have less than 1 degree of freedom. Exiting.")
    if args.verb > 0 and sort:
        print("Warning! Molecule geometries are not sorted.")

    # Check for isomorphism
    for molecule_a, molecule_b in zip(molecules, molecules[1:]):
        g_a = molecule_a.graph
        g_b = molecule_b.graph
        if nx.is_isomorphic(g_a, g_b):
            continue
        else:
            if args.verb > 0:
                print("Warning! Molecule topologies are not isomorphic.")
            isomorph = False
            break
        isomorph = True

    # Double check if energies are properly set
    energies = [molecule.energy for molecule in molecules]
    if None in energies:
        if args.verb > 2:
            print(f"Energies are: {energies}")

    # Check input args typing/values
    valid_c = ["kmeans", "agglomerative", "affprop"]
    if args.c not in valid_c:
        raise InputError(
            f"Unknown clustering algorithm selected. Valid algorithms are:\n {valid_c}\n Exiting."
        )

    valid_m = ["rmsd", "erel", "da", "ewrmsd", "ewda", "mix"]
    if args.m not in valid_m:
        raise InputError(
            f"Unknown metric for clustering selected. Valid metrics are:\n {valid_m}\n Exiting."
        )

    if args.n is not None:
        try:
            n = int(args.n)
        except ValueError:
            raise InputError(
                f"n must be an integer or None, but {n} was provided. Exiting."
            )
    else:
        n = None

    return (
        basename,
        np.array(molecules, dtype=object),
        dof,
        args.c,
        args.m,
        n,
        ewin,
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
