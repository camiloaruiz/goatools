
# Copyright (C) 2010-2018 by Haibao Tang et al. All rights reserved.
#
# This code is part of the goatools distribution and goverend by its
# license. Please see the LICENSE file included with goatools.


"""Read and store Gene Ontology's obo file."""
# -*- coding: UTF-8 -*-
from __future__ import print_function

import sys
import os
from goatools.godag.obo_optional_attributes import OboOptionalAttrs
from goatools.godag.typedef import TypeDef
from goatools.godag.typedef import add_to_typedef
import networkx as nx

GraphEngines = ("pygraphviz", "pydot")

__copyright__ = "Copyright (C) 2010-2018, H Tang et al., All rights reserved."
__author__ = "various"


OBO_FILE = "/dfs/scratch2/caruiz/databases/go-basic.obo"

PART_OF = "part_of"
REGULATES = "regulates"
POSITIVELY_REGULATES = "positively_regulates"
NEGATIVELY_REGULATES = "negatively_regulates"

#pylint: disable=too-few-public-methods
class OBOReader(object):
    """Read goatools.org's obo file. Load into this iterable class.

        Download obo from: http://geneontology.org/ontology/go-basic.obo

        >>> reader = OBOReader()
        >>> for rec in reader:
                print(rec)
    """

    # Scalar attributes for Typedefs:
    #                    'is_class_level', 'is_metadata_tag',
    #                    'is_transitive', 'transitive_over'])

    def __init__(self, obo_file=OBO_FILE, optional_attrs=None):
        """Read obo file. Load dictionary."""
        self.optobj = self._init_optional_attrs(optional_attrs)  # OboOptionalAttrs or None
        self.format_version = None # e.g., "1.2" of "format-version:" line
        self.data_version = None # e.g., "releases/2016-07-07" from "data-version:" line
        self.typedefs = {}

        # True if obo file exists or if a link to an obo file exists.
        print("obo_file:")
        print(obo_file)
        if os.path.isfile(obo_file):
            self.obo_file = obo_file
            # GOTerm attributes that are necessary for any operations:
        else:
            raise Exception("COULD NOT READ({OBO})\n"
                            "download obo file first\n "
                            "[http://geneontology.org/ontology/"
                            "go-basic.obo]".format(OBO=obo_file))

    def __iter__(self):
        """Return one GO Term record at a time from an obo file."""
        # Wait to open file until needed. Automatically close file when done.
        with open(self.obo_file) as fstream:
            rec_curr = None # Stores current GO Term
            typedef_curr = None  # Stores current typedef
            for line in fstream:
                # obo lines start with any of: [Term], [Typedef], /^\S+:/, or /^\s*/
                if self.data_version is None:
                    self._init_obo_version(line)
                if rec_curr is None and line[0:6].lower() == "[term]":
                    rec_curr = GOTerm()
                    if self.optobj:
                        self.optobj.init_datamembers(rec_curr)
                elif typedef_curr is None and line[0:9].lower() == "[typedef]":
                    typedef_curr = TypeDef()
                elif rec_curr is not None or typedef_curr is not None:
                    line = line.rstrip()  # chomp
                    if line:
                        self._add_to_obj(rec_curr, typedef_curr, line)
                    else:
                        if rec_curr is not None:
                            yield rec_curr
                            rec_curr = None
                        elif typedef_curr is not None:
                            # Save typedef.
                            self.typedefs[typedef_curr.id] = typedef_curr
                            typedef_curr = None
            # Return last record, if necessary
            if rec_curr is not None:
                yield rec_curr

    def _add_to_obj(self, rec_curr, typedef_curr, line):
        """Add information on line to GOTerm or Typedef."""
        if rec_curr is not None:
            self._add_to_ref(rec_curr, line)
        else:
            add_to_typedef(typedef_curr, line)

    def _init_obo_version(self, line):
        """Save obo version and release."""
        if line[0:14] == "format-version":
            self.format_version = line[16:-1]
        if line[0:12] == "data-version":
            self.data_version = line[14:-1]

    def _add_to_ref(self, rec_curr, line):
        """Add new fields to the current reference."""
        # Examples of record lines containing ':' include:
        #   id: GO:0000002
        #   name: mitochondrial genome maintenance
        #   namespace: biological_process
        #   def: "The maintenance of ...
        #   is_a: GO:0007005 ! mitochondrion organization
        if line[:4] == "id: ":
            assert not rec_curr.id
            rec_curr.id = line[4:]
        elif line[:8] == "alt_id: ":
            rec_curr.alt_ids.add(line[8:])
        elif line[:6] == "name: ":
            assert not rec_curr.name
            rec_curr.name = line[6:]
        elif line[:11] == "namespace: ":
            assert not rec_curr.namespace
            rec_curr.namespace = line[11:]
        elif line[:6] == "is_a: ":
            rec_curr._parents.add(line[6:].split()[0])
        elif line[:13] == "is_obsolete: " and line[13:] == "true":
            rec_curr.is_obsolete = True
        elif self.optobj and ':' in line:
            self.optobj.update_rec(rec_curr, line)

    @staticmethod
    def _init_optional_attrs(optional_attrs):
        """Create OboOptionalAttrs or return None."""
        if optional_attrs is None:
            return None
        opts = OboOptionalAttrs.get_optional_attrs(optional_attrs)
        if opts:
            return OboOptionalAttrs(opts)


class GOTerm(object):
    """
    GO term, actually contain a lot more properties than interfaced here
    """

    def __init__(self):
        self.id = ""                # GO:NNNNNNN
        self.name = ""              # description
        self.namespace = ""         # BP, CC, MF
        self._parents = set()       # is_a basestring of parents
        self.parents = set()        # parent records
        self.children = set()       # children records
        self.level = None           # shortest distance from root node
        self.depth = None           # longest distance from root node
        self.is_obsolete = False    # is_obsolete
        self.alt_ids = set()        # alternative identifiers

    def __str__(self):
        ret = ['{GO}\t'.format(GO=self.id)]
        if self.level is not None:
            ret.append('level-{L:>02}\t'.format(L=self.level))
        if self.depth is not None:
            ret.append('depth-{D:>02}\t'.format(D=self.depth))
        ret.append('{NAME} [{NS}]'.format(NAME=self.name, NS=self.namespace))
        if self.is_obsolete:
            ret.append('obsolete')
        return ''.join(ret)

    def __repr__(self):
        """Print GO id and all attributes in GOTerm class."""
        ret = ["GOTerm('{ID}'):".format(ID=self.id)]
        for key, val in self.__dict__.items():
            if isinstance(val, int) or isinstance(val, str):
                ret.append("{K}:{V}".format(K=key, V=val))
            elif val is not None:
                ret.append("{K}: {V} items".format(K=key, V=len(val)))
                if len(val) < 10:
                    if not isinstance(val, dict):
                        for elem in val:
                            ret.append("  {ELEM}".format(ELEM=elem))
                    else:
                        for (typedef, terms) in val.items():
                            ret.append("  {TYPEDEF}: {NTERMS} items"
                                       .format(TYPEDEF=typedef,
                                               NTERMS=len(terms)))
                            for term in terms:
                                ret.append("    {TERM}".format(TERM=term))
            else:
                ret.append("{K}: None".format(K=key))
        return "\n  ".join(ret)

    def has_parent(self, term):
        """Return True if this GO object has a parent GO ID."""
        for parent in self.parents:
            if parent.id == term or parent.has_parent(term):
                return True
        return False

    def has_child(self, term):
        """Return True if this GO object has a child GO ID."""
        for parent in self.children:
            if parent.id == term or parent.has_child(term):
                return True
        return False

    def get_all_parents(self):
        """Return all parent GO IDs."""
        all_parents = set()
        for parent in self.parents:
            all_parents.add(parent.id)
            all_parents |= parent.get_all_parents()
        return all_parents

    def get_k_parents(self, k = None):
        """Gets parent GO IDs up to k levels back"""
        if k is None:
            return self.get_all_parents()
        else:
            k_parents = set()
            cur_parents = self.parents
            cur_parents_ids = [cur_parent.id for cur_parent in cur_parents]

            for i in range(0, k):
                k_parents.update(cur_parents_ids)

                new_cur_parents = set()
                for cur_parent in cur_parents:
                    new_cur_parents.update(cur_parent.parents)
                cur_parents = new_cur_parents
                cur_parents_ids = [cur_parent.id for cur_parent in cur_parents]
            return k_parents

    def get_part_of_parents(self):
        if not(PART_OF in self.relationship):
            return set()
        else:
            return self.relationship[PART_OF]

    def get_k_part_of_parents(self, k = None):
        k_part_of_parents = set()
        cur_part_of_parents = self.get_part_of_parents()
        cur_part_of_parents_ids = [cur_part_of_parent.id for cur_part_of_parent in cur_part_of_parents]

        for i in range(0, k):
            k_part_of_parents.update(cur_part_of_parents_ids)

            new_cur_part_of_parents = set()
            for cur_part_of_parent in cur_part_of_parents:
                new_cur_part_of_parents.update(cur_part_of_parent.get_part_of_parents())
            cur_part_of_parents = new_cur_part_of_parents
            cur_part_of_parents_ids = [cur_part_of_parent.id for cur_part_of_parent in cur_part_of_parents]

        return k_part_of_parents

    def get_all_upper(self):
        """Return all parent GO IDs through both 'is_a' and all relationships."""
        all_upper = set()
        for upper in self.get_goterms_upper():
            all_upper.add(upper.id)
            all_upper |= upper.get_all_upper()
        return all_upper

    def get_all_children(self):
        """Return all children GO IDs."""
        all_children = set()
        for parent in self.children:
            all_children.add(parent.id)
            all_children |= parent.get_all_children()
        return all_children

    def get_k_children(self, k = None):
        if k is None:
            return self.get_all_children()
        else:
            k_children = set()
            cur_children = self.children
            cur_children_ids = [cur_child.id for cur_child in cur_children]

            for i in range(0, k):
                k_children.update(cur_children_ids)

                new_cur_children = set()
                for cur_child in cur_children:
                    new_cur_children.update(cur_child.children)
                cur_children = new_cur_children
                cur_children_ids = [cur_child.id for cur_child in cur_children]
            return k_children

    def get_all_lower(self):
        """Return all parent GO IDs through both reverse 'is_a' and all relationships."""
        all_lower = set()
        for lower in self.get_goterms_lower():
            all_lower.add(lower.id)
            all_lower |= lower.get_all_lower()
        return all_lower

    def get_all_parent_edges(self):
        """Return tuples for all parent GO IDs, containing current GO ID and parent GO ID."""
        all_parent_edges = set()
        for parent in self.parents:
            all_parent_edges.add((self.id, parent.id))
            all_parent_edges |= parent.get_all_parent_edges()
        return all_parent_edges

    def get_all_child_edges(self):
        """Return tuples for all child GO IDs, containing current GO ID and child GO ID."""
        all_child_edges = set()
        for parent in self.children:
            all_child_edges.add((parent.id, self.id))
            all_child_edges |= parent.get_all_child_edges()
        return all_child_edges

    def get_goterms_upper(self):
        """Returns a set containing parents and relationship GO Terms."""
        # Requires GODag is created with 'relationship' in optional_attrs argument
        # pylint: disable=no-member
        return set.union(self.parents, *self.relationship.values())

    def get_goterms_lower(self):
        """Returns a set containing children and reverse-relationship GO Terms."""
        # Requires GODag is created with 'relationship' in optional_attrs argument
        # pylint: disable=no-member
        return set.union(self.children, *self.relationship_rev.values())


    def write_hier_rec(self, gos_printed, out=sys.stdout,
                       len_dash=1, max_depth=None, num_child=None, short_prt=False,
                       include_only=None, go_marks=None,
                       depth=1, depth_dashes="-"):
        """Write hierarchy for a GO Term record."""
        # Added by DV Klopfenstein
        goid = self.id
        # Shortens hierarchy report by only printing the hierarchy
        # for the sub-set of user-specified GO terms which are connected.
        if include_only is not None and goid not in include_only:
            return
        nrp = short_prt and goid in gos_printed
        if go_marks is not None:
            out.write('{} '.format('>' if goid in go_marks else ' '))
        if len_dash is not None:
            # Default character indicating hierarchy level is '-'.
            # '=' is used to indicate a hierarchical path printed in detail previously.
            letter = '-' if not nrp or not self.children else '='
            depth_dashes = ''.join([letter]*depth)
            out.write('{DASHES:{N}} '.format(DASHES=depth_dashes, N=len_dash))
        if num_child is not None:
            out.write('{N:>5} '.format(N=len(self.get_all_children())))
        out.write('{GO}\tL-{L:>02}\tD-{D:>02}\t{desc}\n'.format(
            GO=self.id, L=self.level, D=self.depth, desc=self.name))
        # Track GOs previously printed only if needed
        if short_prt:
            gos_printed.add(goid)
        # Do not print hierarchy below this turn if it has already been printed
        if nrp:
            return
        depth += 1
        if max_depth is not None and depth > max_depth:
            return
        for child in self.children:
            child.write_hier_rec(gos_printed, out, len_dash, max_depth, num_child, short_prt,
                                 include_only, go_marks,
                                 depth, depth_dashes)

class GODag(dict):
    """Holds the GO DAG as a dict."""

    def __init__(self, obo_file=OBO_FILE, optional_attrs=None, load_obsolete=False, prt=sys.stdout):
        super(GODag, self).__init__()
        self.version = self.load_obo_file(obo_file, optional_attrs, load_obsolete, prt)

    def load_obo_file(self, obo_file, optional_attrs, load_obsolete, prt):
        """Read obo file. Store results."""
        reader = OBOReader(obo_file, optional_attrs)

        # Save alt_ids and their corresponding main GO ID. Add to GODag after populating GO Terms
        alt2rec = {}
        i = 0
        for rec in reader:
            # Save record if:
            #   1) Argument load_obsolete is True OR
            #   2) Argument load_obsolete is False and the GO term is "live" (not obsolete)
            if load_obsolete or not rec.is_obsolete:
                self[rec.id] = rec
                for alt in rec.alt_ids:
                    alt2rec[alt] = rec

        # Save the typedefs and parsed optional_attrs
        # self.optobj = reader.optobj
        self.typedefs = reader.typedefs
        self._populate_terms(reader.optobj)
        self._set_level_depth(reader.optobj)

        # Add alt_ids to go2obj
        for goid_alt, rec in alt2rec.items():
            self[goid_alt] = rec
        desc = self._str_desc(reader)
        if prt is not None:
            prt.write("{DESC}\n".format(DESC=desc))
        return desc

    def _str_desc(self, reader):
        """String containing information about the current GO DAG."""
        data_version = reader.data_version
        if data_version is not None:
            data_version = data_version.replace("releases/", "")
        desc = "{OBO}: fmt({FMT}) rel({REL}) {N:,} GO Terms".format(
            OBO=reader.obo_file, FMT=reader.format_version,
            REL=data_version, N=len(self))
        if reader.optobj:
            desc = "{D}; optional_attrs({A})".format(D=desc, A=" ".join(sorted(reader.optobj.optional_attrs)))
        return desc


    def _populate_terms(self, optobj):
        """Convert GO IDs to GO Term record objects. Populate children."""
        has_relationship = optobj is not None and 'relationship' in optobj.optional_attrs
        # Make parents and relationships references to the actual GO terms.
        for rec in self.values():
            # Given parent GO IDs, set parent GO Term objects
            rec.parents = set([self[goid] for goid in rec._parents])

            # For each parent GO Term object, add it's child GO Term to the children data member
            for parent_rec in rec.parents:
                parent_rec.children.add(rec)

            if has_relationship:
                self._populate_relationships(rec)

    def _populate_relationships(self, rec_curr):
        """Convert GO IDs in relationships to GO Term record objects. Populate children."""
        for relationship_type, goids in rec_curr.relationship.items():
            parent_recs = set([self[goid] for goid in goids]) 
            rec_curr.relationship[relationship_type] = parent_recs # replace GO ID with GO Term record object
            for parent_rec in parent_recs:
                if relationship_type not in parent_rec.relationship_rev:
                    parent_rec.relationship_rev[relationship_type] = set([rec_curr])
                else:
                    parent_rec.relationship_rev[relationship_type].add(rec_curr)

    def _set_level_depth(self, optobj):
        """Set level, depth and add inverted relationships."""
        has_relationship = optobj is not None and 'relationship' in optobj.optional_attrs

        def _init_level(rec):
            if rec.level is None:
                if rec.parents:
                    rec.level = min(_init_level(rec) for rec in rec.parents) + 1
                else:
                    rec.level = 0
            return rec.level

        def _init_depth(rec):
            if rec.depth is None:
                if rec.parents:
                    rec.depth = max(_init_depth(rec) for rec in rec.parents) + 1
                else:
                    rec.depth = 0
            return rec.depth

        def _init_reldepth(rec):
            if not hasattr(rec, 'reldepth'):
                up_terms = rec.get_goterms_upper()
                if up_terms:
                    rec.reldepth = max(_init_reldepth(rec) for rec in up_terms) + 1
                else:
                    rec.reldepth = 0
            return rec.reldepth

        for rec in self.values():

            # Add invert relationships
            if has_relationship:
                if rec.depth is None:
                    _init_reldepth(rec)

                # print("BBBBBBBBBBB1", rec.id, rec.relationship)
                #for (typedef, terms) in rec.relationship.items():
                #    invert_typedef = self.typedefs[typedef].inverse_of
                #    # print("BBBBBBBBBBB2 {} ({}) ({}) ({})".format(
                #    #    rec.id, rec.relationship, typedef, invert_typedef))
                #    if invert_typedef:
                #        # Add inverted relationship
                #        for term in terms:
                #            if not hasattr(term, 'relationship'):
                #                term.relationship = defaultdict(set)
                #            term.relationship[invert_typedef].add(rec)
                # print("BBBBBBBBBBB3", rec.id, rec.relationship)

            if rec.level is None:
                _init_level(rec)

            if rec.depth is None:
                _init_depth(rec)

    def write_dag(self, out=sys.stdout):
        """Write info for all GO Terms in obo file, sorted numerically."""
        for rec in sorted(self.values()):
            print(rec, file=out)

    def write_hier_all(self, out=sys.stdout,
                       len_dash=1, max_depth=None, num_child=None, short_prt=False):
        """Write hierarchy for all GO Terms in obo file."""
        # Print: [biological_process, molecular_function, and cellular_component]
        for go_id in ['GO:0008150', 'GO:0003674', 'GO:0005575']:
            self.write_hier(go_id, out, len_dash, max_depth, num_child, short_prt, None)

    def write_hier(self, go_id, out=sys.stdout,
                   len_dash=1, max_depth=None, num_child=None, short_prt=False,
                   include_only=None, go_marks=None):
        """Write hierarchy for a GO Term."""
        gos_printed = set()
        self[go_id].write_hier_rec(gos_printed, out, len_dash, max_depth, num_child,
                                   short_prt, include_only, go_marks)

    @staticmethod
    def id2int(go_id):
        """Given a GO ID, return the int value."""
        return int(go_id.replace("GO:", "", 1))

    def query_term(self, term, verbose=False):
        """Given a GO ID, return GO object."""
        if term not in self:
            sys.stderr.write("Term %s not found!\n" % term)
            return

        rec = self[term]
        if verbose:
            print(rec)
            sys.stderr.write("all parents: {}\n".format(
                repr(rec.get_all_parents())))
            sys.stderr.write("all children: {}\n".format(
                repr(rec.get_all_children())))
        return rec

    def paths_to_top(self, term):
        """ Returns all possible paths to the root node

            Each path includes the term given. The order of the path is
            top -> bottom, i.e. it starts with the root and ends with the
            given term (inclusively).

            Parameters:
            -----------
            - term:
                the id of the GO term, where the paths begin (i.e. the
                accession 'GO:0003682')

            Returns:
            --------
            - a list of lists of GO Terms
        """
        # error handling consistent with original authors
        if term not in self:
            sys.stderr.write("Term %s not found!\n" % term)
            return

        def _paths_to_top_recursive(rec):
            if rec.level == 0:
                return [[rec]]
            paths = []
            for parent in rec.parents:
                top_paths = _paths_to_top_recursive(parent)
                for top_path in top_paths:
                    top_path.append(rec)
                    paths.append(top_path)
            return paths

        go_term = self[term]
        return _paths_to_top_recursive(go_term)

    def label_wrap(self, label):
        """Label text for plot."""
        wrapped_label = r"%s\n%s" % (label,
                                     self[label].name.replace(",", r"\n"))
        return wrapped_label

    def make_graph_networkx(self, allowed_relationship_types):
        grph = nx.DiGraph()
        print("Making graph!")
        for A_rec in self.values():
            # Add node if not already in graph
            # Must be done separately for isolated nodes
            if not(A_rec.id in grph.nodes()):
                grph.add_node(A_rec.id)

            # Add edges
            for relationship_type, B_recs in A_rec.relationship.items():
                if relationship_type in allowed_relationship_types:
                    for B_rec in B_recs:
                        grph.add_edge(A_rec.id, B_rec.id)
        return grph

    def make_graph_pydot(self, recs, nodecolor,
                         edgecolor, dpi,
                         draw_parents=True, draw_children=True):
        """draw AMIGO style network, lineage containing one query record."""
        import pydot
        grph = pydot.Dot(graph_type='digraph', dpi="{}".format(dpi)) # Directed Graph
        edgeset = set()
        usr_ids = [rec.id for rec in recs]
        for rec in recs:
            if draw_parents:
                edgeset.update(rec.get_all_parent_edges())
            if draw_children:
                edgeset.update(rec.get_all_child_edges())

        rec_id_set = set([rec_id for endpts in edgeset for rec_id in endpts])
        nodes = {str(ID):pydot.Node(
            self.label_wrap(ID).replace("GO:", ""),  # Node name
            shape="box",
            style="rounded, filled",
            # Highlight query terms in plum:
            fillcolor="beige" if ID not in usr_ids else "plum",
            color=nodecolor)
                 for ID in rec_id_set}

        # add nodes explicitly via add_node
        for rec_id, node in nodes.items():
            grph.add_node(node)

        for src, target in edgeset:
            # default layout in graphviz is top->bottom, so we invert
            # the direction and plot using dir="back"
            grph.add_edge(pydot.Edge(nodes[target], nodes[src],
                                     shape="normal",
                                     color=edgecolor,
                                     label="is_a",
                                     dir="back"))

        return grph

    def make_graph_pygraphviz(self, recs, nodecolor,
                              edgecolor, dpi,
                              draw_parents=True, draw_children=True):
        """Draw AMIGO style network, lineage containing one query record."""
        import pygraphviz as pgv

        grph = pgv.AGraph(name="GO tree")

        edgeset = set()
        for rec in recs:
            if draw_parents:
                edgeset.update(rec.get_all_parent_edges())
            if draw_children:
                edgeset.update(rec.get_all_child_edges())

        edgeset = [(self.label_wrap(a), self.label_wrap(b))
                   for (a, b) in edgeset]

        # add nodes explicitly via add_node
        # adding nodes implicitly via add_edge misses nodes
        # without at least one edge
        for rec in recs:
            grph.add_node(self.label_wrap(rec.id))

        for src, target in edgeset:
            # default layout in graphviz is top->bottom, so we invert
            # the direction and plot using dir="back"
            grph.add_edge(target, src)

        grph.graph_attr.update(dpi="%d" % dpi)
        grph.node_attr.update(shape="box", style="rounded,filled",
                              fillcolor="beige", color=nodecolor)
        grph.edge_attr.update(shape="normal", color=edgecolor,
                              dir="back", label="is_a")
        # highlight the query terms
        for rec in recs:
            try:
                node = grph.get_node(self.label_wrap(rec.id))
                node.attr.update(fillcolor="plum")
            except:
                continue

        return grph

    def draw_lineage(self, recs, nodecolor="mediumseagreen",
                     edgecolor="lightslateblue", dpi=96,
                     lineage_img="GO_lineage.png", engine="pygraphviz",
                     gml=False, draw_parents=True, draw_children=True):
        """Draw GO DAG subplot."""
        assert engine in GraphEngines
        grph = None
        if engine == "pygraphviz":
            grph = self.make_graph_pygraphviz(recs, nodecolor, edgecolor, dpi,
                                              draw_parents=draw_parents,
                                              draw_children=draw_children)
        else:
            grph = self.make_graph_pydot(recs, nodecolor, edgecolor, dpi,
                                         draw_parents=draw_parents, draw_children=draw_children)

        if gml:
            import networkx as nx  # use networkx to do the conversion
            gmlbase = lineage_img.rsplit(".", 1)[0]
            obj = nx.from_agraph(grph) if engine == "pygraphviz" else nx.from_pydot(grph)

            del obj.graph['node']
            del obj.graph['edge']
            gmlfile = gmlbase + ".gml"
            nx.write_gml(self.label_wrap, gmlfile)
            sys.stderr.write("GML graph written to {0}\n".format(gmlfile))

        sys.stderr.write(("lineage info for terms %s written to %s\n" %
                          ([rec.id for rec in recs], lineage_img)))

        if engine == "pygraphviz":
            grph.draw(lineage_img, prog="dot")
        else:
            grph.write_png(lineage_img)

    def update_association(self, association):
        """Add the GO parents of a gene's associated GO IDs to the gene's association."""
        bad_goids = set()
        # Loop through all sets of GO IDs for all genes
        for goids in association.values():
            parents = set()
            # Iterate thru each GO ID in the current gene's association
            for goid in goids:
                try:
                    parents.update(self[goid].get_all_parents())
                except:
                    bad_goids.add(goid.strip())
            # Add the GO parents of all GO IDs in the current gene's association
            goids.update(parents)
        if bad_goids:
            sys.stdout.write("{N} GO IDs in assc. are not found in the GO-DAG: {GOs}\n".format(
                N=len(bad_goids), GOs=" ".join(bad_goids)))

    def update_k_association(self, association, k):
        """Add the GO parents of a gene's associated GO IDs to the gene's association."""
        if k is None:
            self.update_association(association)
        else:
            bad_goids = set()
            # Loop through all sets of GO IDs for all genes
            for goids in association.values():
                parents = set()
                # Iterate thru each GO ID in the current gene's association
                for goid in goids:
                    try:
                        cur_parents = self[goid]._parents
                        for i in range(0, k):
                            # Add cur_parents 
                            parents.update(cur_parents)
                            # Update cur_parents so we can operate recursively
                            new_cur_parents = set()
                            for cur_parent in cur_parents:
                                new_cur_parents.update(self[cur_parent]._parents)
                            cur_parents = new_cur_parents
                    except:
                        bad_goids.add(goid.strip())
                # Add the GO parents of all GO IDs in the current gene's association
                goids.update(parents)
            if bad_goids:
                sys.stdout.write("{N} GO IDs in assc. are not found in the GO-DAG: {GOs}\n".format(
                    N=len(bad_goids), GOs=" ".join(bad_goids)))


    def get_alt_id_to_master_id_dict(self):
        # Define master IDs as outermost from obodag
        alt_id_to_master_id_dict = dict()

        for rec in self.values():
            # Map the master id to itself
            alt_id_to_master_id_dict[rec.id] = rec.id

            # If record has alternate ids, map the alternate ids to the master id
            if len(rec.alt_ids) > 0:
                for alt_id in rec.alt_ids:
                    alt_id_to_master_id_dict[alt_id] = rec.id

        return alt_id_to_master_id_dict

    def add_forward_reverse_relationship(self, source_rec, sink_rec, relationship_type):
        # Forward
        if relationship_type not in source_rec.relationship:
            source_rec.relationship[relationship_type] = set([sink_rec])
        else:
            source_rec.relationship[relationship_type].add(sink_rec)

        # Reverse
        if relationship_type not in sink_rec.relationship_rev:
            sink_rec.relationship_rev[relationship_type] = set([source_rec])
        else:
            sink_rec.relationship_rev[relationship_type].add(source_rec)

    def propagate_relationship_is_a(self, relationship_types, k_parents = None):
        # If A relationship B and B is C, then A relationship C
        # For each A
        inferred_relationships = []
        for A_rec in self.values():
            # If A relationship B
            for relationship_type, B_recs in A_rec.relationship.items():
                if relationship_type in relationship_types:
                    # For each B
                    for B_rec in B_recs.copy():
                        C_ids = B_rec.get_k_parents(k_parents)
                        for C_id in C_ids:
                            C_rec = self[C_id]

                            # A relationship C
                            inferred_relationships.append((A_rec, C_rec, relationship_type))
        return inferred_relationships

    def propagate_is_a_relationship(self, relationship_types, k_children = None):
        # If A is B and B relationship C, then A relationship C
        # For each B
        inferred_relationships = []
        for B_rec in self.values():
            # If B relationship C
            for relationship_type, C_recs in B_rec.relationship.items():
                if relationship_type in relationship_types:
                    # A relationship C
                    A_ids = B_rec.get_k_children(k_children)
                    for C_rec in C_recs.copy():
                        for A_id in A_ids:
                            A_rec = self[A_id]
                            inferred_relationships.append((A_rec, C_rec, relationship_type))

        return inferred_relationships

    def propagate_regulates_is_a(self, k_parents = None):
        # If A regulates (R/R+/R-) B and B is C, then A regulates (R/R+/R-) C
        return self.propagate_relationship_is_a([REGULATES, POSITIVELY_REGULATES, NEGATIVELY_REGULATES], k_parents)

    def propagate_is_a_regulates(self, k_children = None):
        # If A is B and B regulates(R/R+/R-) C, then A regulates (R/R+/R-) C
        return self.propagate_is_a_relationship([REGULATES, POSITIVELY_REGULATES, NEGATIVELY_REGULATES], k_children)

    def propagate_part_of_is_a(self, k_parents = None):
        return self.propagate_relationship_is_a([PART_OF], k_parents)

    def propagate_is_a_part_of(self, k_children = None):
        return self.propagate_is_a_relationship([PART_OF], k_children)

    def propagate_part_of_part_of(self):
        # In practice, we don't use this method
        # Instead, we write a "get_k_part_of_parents()" method that is subsequently used in propagate_regulates_part_of

        # If A is part of B and B is part of C, then A is part of C
        # For each A
        # These are all direct propagation
        for A_rec in self.values():
            # If A is part of B
            if PART_OF in A_rec.relationship.keys():
                B_recs = A_rec.relationship[PART_OF]
                # and B is part of C
                for B_rec in B_recs.copy():
                    if PART_OF in B_rec.relationship.keys():
                        C_recs = B_rec.relationship[PART_OF]
                        for C_rec in C_recs:
                            # A is part of C
                            inferred_relationships.append((A_rec, C_rec, PART_OF))

        return inferred_relationships

    def propagate_regulates_part_of(self, k_parents = None):
        # If A regulates (R/R+/R-) B and B is part of C, then A regulates (R) C
        # "Levels to propagate" will already have been taken care of here by previous "part of" relationship propagations
        inferred_relationships = []

        for A_rec in self.values():
            # If A regulates B
            for relationship_type, B_recs in A_rec.relationship.items():
                if relationship_type in [REGULATES, POSITIVELY_REGULATES, NEGATIVELY_REGULATES]:
                    for B_rec in B_recs.copy():
                        # and B is part of C
                        if PART_OF in B_rec.relationship.keys():
                            C_ids = B_rec.get_k_part_of_parents(k_parents)
                            for C_id in C_ids:
                                C_rec = self[C_id]

                                inferred_relationships.append((A_rec, C_rec, REGULATES))

        return inferred_relationships

    def add_inferred_relationships(self, inferred_relationships):
        # inferred_relationships takes the form
        # [(source_rec, sink_rec, relationship_type)]
        for source_rec, sink_rec, relationship_type in inferred_relationships:
            self. add_forward_reverse_relationship(source_rec, sink_rec, relationship_type)

    def propagate_all_regulatory_relationships(self, k_parents = None, k_children = None, homogenize = False):
        inferred_relationships = []
        
        # Regulatory Logic
        print("propagate_is_a_regulates...")
        inferred_relationships += self.propagate_is_a_regulates(k_children)
        print("propagate_regulates_is_a...")
        inferred_relationships += self.propagate_regulates_is_a(k_parents)

        # Part of Logic
        print("propagate_part_of_is_a...")
        inferred_relationships += self.propagate_part_of_is_a(k_parents)
        print("propagate_is_a_part_of...")
        inferred_relationships += self.propagate_is_a_part_of(k_children)
        print("propagate_regulates_part_of...")
        inferred_relationships += self.propagate_regulates_part_of(k_parents)

        # Update obodag now
        self.add_inferred_relationships(inferred_relationships)

        # Homogenize
        if (homogenize):
            self.homogonenize_regulatory_relationships()

# Copyright (C) 2010-2018, H Tang et al., All rights reserved.
