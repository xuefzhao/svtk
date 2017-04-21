"""
std_manta.py

Standardize a Manta record.

Copyright © 2017 Matthew Stone <mstone5@mgh.harvard.edu>
Distributed under terms of the MIT license.
"""


from collections import deque
from .standardize import VCFStandardizer, parse_bnd_pos, parse_bnd_strands


@VCFStandardizer.register('manta')
class MantaStandardizer(VCFStandardizer):
    def standardize_vcf(self):
        """
        Filter Manta VCF.

        Mated events are not marked with SECONDARY tag; must filter manually.
        """

        mate_IDs = deque()
        for record in self.raw_vcf:
            # Filter unmarked SECONDARY on same chromosome
            # TODO: Check if necessary to filter diff chromosomes
            if 'MATEID' in record.info:
                mate_ID = record.info['MATEID']

                # Skip records with an observed mate
                if mate_ID in mate_IDs:
                    continue

                # Track mates of observed records
                mate_IDs.append(mate_ID)

            std_rec = self.std_vcf.new_record()
            yield self.standardize_record(std_rec, record)

    def standardize_info(self, std_rec, raw_rec):
        """
        Standardize Manta record.

        1) Replace colons in ID with underscores (otherwise breaks VCF parsing)
        2) Define CHR2 and END
        3) Add strandedness
        4) Add SVLEN
        """

        # Colons in the ID can break parsing
        std_rec.id = '_'.join(std_rec.id.split(':'))

        try:
            svtype = raw_rec.info['SVTYPE']
        except:
            import ipdb
            ipdb.set_trace()
        std_rec.info['SVTYPE'] = svtype

        # Define CHR2 and END
        if svtype == 'BND':
            chr2, end = parse_bnd_pos(raw_rec.alts[0])
            alt = raw_rec.alts[0].strip('ATCGN')
            # Strip brackets separately, otherwise GL contigs will be altered
            alt = alt.strip('[]')
            chr2, end = alt.split(':')
            end = int(end)
        else:
            chr2 = raw_rec.chrom
            end = raw_rec.info['END']
        std_rec.info['CHR2'] = chr2
        std_rec.info['END'] = end

        # Strand parsing
        if svtype == 'INV':
            if 'INV3' in raw_rec.info.keys():
                strands = '++'
            else:
                strands = '--'
        elif svtype == 'BND':
            alt = raw_rec.alts[0]
            strands = parse_bnd_strands(raw_rec.alts[0])
        elif svtype == 'DEL':
            strands = '+-'
        elif svtype == 'DUP':
            strands = '-+'
        elif svtype == 'INS':
            strands = '.'
        std_rec.info['STRANDS'] = strands

        if svtype == 'BND' and std_rec.chrom != std_rec.info['CHR2']:
            std_rec.info['SVLEN'] = -1
        else:
            std_rec.info['SVLEN'] = std_rec.info['END'] = std_rec.pos

        std_rec.info['SOURCE'] = 'manta'

        return std_rec