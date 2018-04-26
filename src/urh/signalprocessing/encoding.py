#!/usr/bin/env python3
__author__ = 'andreas.noack@fh-stralsund.de'

import subprocess

from urh import constants
from urh.util.crc import crc_generic


class encoding(object):
    """
    Full featured encoding/decoding of protocols.
    """

    def __init__(self, chain=None):
        if chain is None:
            chain = []

        self.mode = 0
        self.external_decoder = ""
        self.external_encoder = ""
        self.multiple = 1
        self.src = []  # [[True, True], [True, False], [False, True], [False, False]]
        self.dst = []  # [[False, False], [False, True], [True, False], [True, True]]
        self.carrier = []
        self.__symbol_len = 1

        # Configure CC1101 Date Whitening
        polynomial = [False, False, True, False, False, False, False, True] # x^5+x^0
        sync_bytes = [True, True, True, False, True, False, False, True, True, True, False, False,
                      True, False, True, False, True, True, True, False, True, False, False, True,
                      True, True, False, False, True, False, True, False]  # "e9cae9ca"
        #sync_bytes = self.str2bit("01100111011010000110011101101000") # "67686768" (RWE Default)
        #sync_bytes = self.str2bit("01101001111101100110100111110111") # "69f669f7" (Special RWE)

        self.data_whitening_polynomial = polynomial  # Set polynomial
        self.data_whitening_sync = sync_bytes  # Sync Bytes
        self.data_whitening_crc = [False] * 16  # CRC is 16 Bit long
        self.data_whitening_preamble = [True, False] * 16  # 010101...
        self.lfsr_state = []

        self.data_whitening_apply_crc = True # Apply CRC with XOR
        self.data_whitening_preamble_rm = True  # Remove Preamble
        self.data_whitening_sync_rm = True  # Remove Sync Bytes
        self.data_whitening_crc_rm = False  # Remove CRC

        # Get CRC Object
        self.c = crc_generic(polynomial="16_standard", start_value=True)

        # Set Chain
        self.chain = []
        self.set_chain(chain)

    @property
    def symbol_len(self):
        return int(self.__symbol_len)

    @property
    def name(self):
        return self.chain[0]

    @property
    def is_nrz(self) -> bool:
        return len(self.chain) <= 1

    def __str__(self):
        return self.name

    def set_chain(self, names):
        if len(names) < 1:
            return
        self.chain = [names[0]]

        i = 1
        while i < len(names):
            if constants.DECODING_INVERT in names[i]:
                self.chain.append(self.code_invert)
            elif constants.DECODING_DIFFERENTIAL in names[i]:
                self.chain.append(self.code_differential)
            elif constants.DECODING_REDUNDANCY in names[i]:
                self.chain.append(self.code_redundancy)
                i += 1
                if i < len(names):
                    self.chain.append(names[i])
                else:
                    self.chain.append(2)
            elif constants.DECODING_DATAWHITENING in names[i]:
                self.chain.append(self.code_data_whitening)
                i += 1
                if i < len(names):
                    self.chain.append(names[i])
                else:
                    self.chain.append("0xe9cae9ca;0x21;0xe") # Default Sync Bytes
            elif constants.DECODING_CARRIER in names[i]:
                self.chain.append(self.code_carrier)
                i += 1
                if i < len(names):
                    self.chain.append(self.str2bit(names[i]))
                else:
                    self.chain.append(self.str2bit("1"))
            elif constants.DECODING_BITORDER in names[i]:
                self.chain.append(self.code_lsb_first)
            elif constants.DECODING_EDGE in names[i]:
                self.chain.append(self.code_edge)
            elif constants.DECODING_SUBSTITUTION in names[i]:
                self.chain.append(self.code_substitution)
                i += 1
                if i < len(names):
                    self.chain.append(self.get_subst_array(names[i]))
                else:
                    self.chain.append(self.get_subst_array("0:1;1:0;"))
            elif constants.DECODING_EXTERNAL in names[i]:
                self.chain.append(self.code_externalprogram)
                i += 1
                if i < len(names):
                    self.chain.append(names[i])
                else:
                    self.chain.append("./;./")
            i += 1

    def get_chain(self):
        chainstr = [self.name]

        i = 1
        while i < len(self.chain):
            if self.code_invert == self.chain[i]:
                chainstr.append(constants.DECODING_INVERT)
            elif self.code_differential == self.chain[i]:
                chainstr.append(constants.DECODING_DIFFERENTIAL)
            elif self.code_redundancy == self.chain[i]:
                chainstr.append(constants.DECODING_REDUNDANCY)
                i += 1
                chainstr.append(self.chain[i])
            elif self.code_data_whitening == self.chain[i]:
                chainstr.append(constants.DECODING_DATAWHITENING)
                i += 1
                chainstr.append(self.chain[i])
            elif self.code_carrier == self.chain[i]:
                chainstr.append(constants.DECODING_CARRIER)
                i += 1
                chainstr.append(self.bit2str(self.chain[i]))
            elif self.code_lsb_first == self.chain[i]:
                chainstr.append(constants.DECODING_BITORDER)
            elif self.code_edge == self.chain[i]:
                chainstr.append(constants.DECODING_EDGE)
            elif self.code_substitution == self.chain[i]:
                chainstr.append(constants.DECODING_SUBSTITUTION)
                i += 1
                chainstr.append(self.get_subst_string(self.chain[i]))
            elif self.code_externalprogram == self.chain[i]:
                chainstr.append(constants.DECODING_EXTERNAL)
                i += 1
                chainstr.append(self.chain[i])
            i += 1

        return chainstr

    def get_subst_array(self, string):
        src = []
        dst = []
        elements = string.split(";")
        for i in elements:
            if len(i):
                tsrc, tdst = i.split(":")
                src.append(self.str2bit(tsrc))
                dst.append(self.str2bit(tdst))
        return [src, dst]

    def get_subst_string(self, inpt):
        src = inpt[0]
        dst = inpt[1]
        output = ""
        if len(src) == len(dst):
            for i in range(0, len(src)):
                output += self.bit2str(src[i]) + ":" + self.bit2str(dst[i]) + ";"

        return output

    def code(self, decoding, inputbits):
        temp = inputbits.copy()
        output = temp
        errors = 0

        # operation order
        if decoding:
            i = 0
            ops = len(self.chain)
            step = 1
        else:
            i = len(self.chain) - 1
            ops = -1
            step = -1

        # do operations
        while i != ops:
            operation = self.chain[i]
            while not callable(operation) and i + step != ops:
                i += step
                operation = self.chain[i]

            # Ops with parameters
            if self.code_redundancy == operation:
                self.multiple = int(self.chain[i + 1])
            elif self.code_carrier == operation:
                self.carrier = self.str2bit(self.chain[i + 1])
            elif self.code_substitution == operation:
                self.src = self.chain[i + 1][0]
                self.dst = self.chain[i + 1][1]
            elif self.code_externalprogram == operation:
                if self.chain[i + 1] != "":
                    self.external_decoder, self.external_encoder = self.chain[i + 1].split(";")
                else:
                    self.external_decoder, self.external_encoder = "", ""
            elif self.code_data_whitening == operation:
                if self.chain[i + 1].count(';') == 2:
                    self.data_whitening_sync, self.data_whitening_polynomial, opt = self.chain[i + 1].split(";")
                    if(len(self.data_whitening_sync) > 0 and len(self.data_whitening_polynomial) > 0) and len(opt) > 0:
                        self.data_whitening_sync = self.hex2bit(self.data_whitening_sync)
                        self.data_whitening_polynomial = self.hex2bit(self.data_whitening_polynomial)
                        opt = self.hex2bit(opt)
                        if len(opt)>=4:
                            self.data_whitening_apply_crc = opt[0]
                            self.data_whitening_preamble_rm = opt[1]
                            self.data_whitening_sync_rm = opt[2]
                            self.data_whitening_crc_rm = opt[3]

            # Execute Ops
            if callable(operation) and len(temp) > 0:
                output, temp_errors = operation(decoding, temp)
                errors += temp_errors

            # Loop Footer
            i += step
            temp = output

        if len(inputbits):
            self.__symbol_len = len(output) / len(inputbits)
        return output, errors

    def lfsr(self, clock):
        poly = [False]
        poly.extend(self.data_whitening_polynomial)
        len_pol = len(poly)

        if len(self.lfsr_state) == 0:
            self.lfsr_state.extend([True] * len_pol)
        for i in range(0, clock):
            # Determine first bit with polynomial
            first_bit = -1
            for j in range(len_pol - 1, 0, -1):
                if poly[j] and self.lfsr_state[j]:
                    if first_bit == -1:
                        first_bit = True
                    else:
                        first_bit = not first_bit
            if first_bit == -1:
                first_bit = False
            # Clock
            for j in range(len_pol - 1, 0, -1):
                self.lfsr_state[j] = self.lfsr_state[j - 1]
            self.lfsr_state[0] = first_bit
        return self.lfsr_state[1:len_pol]

    def apply_data_whitening(self, decoding, inpt):
        len_sync = len(self.data_whitening_sync)
        len_polynomial = len(self.data_whitening_polynomial)
        inpt_from = 0
        inpt_to = len(inpt)

        # Crop last bit, if duplicate
        if decoding and inpt_to > 1:
            if inpt[-1] == inpt[-2]:
                inpt_to -= 1

        # inpt empty, polynomial or syncbytes are zero! (Shouldn't happen)
        if inpt_to < 1 or len_polynomial < 1 or len_sync < 1:
            return inpt[inpt_from:inpt_to], 31337   # Error 31337

        # Force inpt to contain bool values; overwrite everything else with True
        for i in range(0, inpt_to):
            if not isinstance(inpt[i], bool):
                inpt[i] = True

        # Search for whitening start position (after sync bytes)
        whitening_start_pos = inpt_from
        i = inpt_from
        while i < (inpt_to - len_sync):
            equalbits = 0
            for j in range(0, len_sync):
                if inpt[i+j] == self.data_whitening_sync[j]:
                    equalbits += 1
                else:
                    continue
            if len_sync == equalbits:
                whitening_start_pos = i+j+1
                break
            else:
                i += 1
        # Sync not found
        if decoding and whitening_start_pos == inpt_from:
            return inpt[inpt_from:inpt_to], 404     # Error 404

        # If encoding and crc_rm is active, extend inpt with 0s
        if not decoding and self.data_whitening_crc_rm:
            inpt = inpt + self.data_whitening_crc
            inpt_to += len(self.data_whitening_crc)

        # Prepare keystream
        self.lfsr_state = []
        keystream = self.lfsr(0)
        for i in range(whitening_start_pos, inpt_to, 8):
            keystream.extend(self.lfsr(8))

        # If data whitening polynomial is wrong, keystream can be less than needed. Check and exit.
        if len(keystream) < inpt_to-whitening_start_pos:
            return inpt[inpt_from:inpt_to], 31338   # Error 31338

        # Apply keystream (xor) - Decoding
        if decoding:
            for i in range(whitening_start_pos, inpt_to):
                inpt[i] ^= keystream[i - whitening_start_pos]

        # Apply CRC-16
        if self.data_whitening_apply_crc:
            # Calculate CRC-16:
            if not decoding and self.data_whitening_crc_rm:
                crc = self.c.crc(inpt[whitening_start_pos:inpt_to])
            else:
                crc = self.c.crc(inpt[whitening_start_pos:inpt_to - len(self.data_whitening_crc)])
            # XOR calculated CRC to original CRC -> Zero if no errors
            for i in range(0, 16):
                inpt[inpt_to - len(self.data_whitening_crc) + i] ^= crc[i]

        # Apply keystream (xor) - Decoding
        if not decoding:
            for i in range(whitening_start_pos, inpt_to):
                inpt[i] ^= keystream[i - whitening_start_pos]

        # Remove preamble/sync bytes/crc
        if decoding:
            if self.data_whitening_preamble_rm:
                inpt_from += whitening_start_pos - len_sync
            if self.data_whitening_sync_rm:
                inpt_from += len_sync
            if self.data_whitening_crc_rm:
                inpt_to -= len(self.data_whitening_crc)
        else:
            if self.data_whitening_sync_rm:
                inpt = self.data_whitening_sync + inpt
                inpt_to += len(self.data_whitening_sync)
            if self.data_whitening_preamble_rm:
                inpt = self.data_whitening_preamble + inpt
                inpt_to += len(self.data_whitening_preamble)
            # Duplicate last bit when encoding
            inpt += [inpt[-1]]
            inpt_to += 1

        return inpt[inpt_from:inpt_to], 0

    def run_command(self, command, param):
        # add shlex.quote(param) later for security reasons
        # print(command, param)
        try:
            p = subprocess.Popen([command + " " + param],
                                 shell=True,
                                 # stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE)
            # stderr=subprocess.PIPE)
            out, _ = p.communicate(param.encode())
            return out.decode()
        except:
            print("Error running", command, param)
            return ""

    def code_carrier(self, decoding, inpt):
        output = []
        errors = 0

        if decoding:
            # Remove carrier if decoding
            if len(self.carrier) > 0:
                for x in range(len(self.carrier), len(inpt), len(self.carrier) + 1):
                    output.append(inpt[x])
        else:
            # Add carrier if encoding
            if len(self.carrier) > 0:
                for i in inpt:
                    output.extend(self.carrier)
                    output.append(i)
                output.extend(self.carrier)
        return output, errors

    def code_data_whitening(self, decoding, inpt):
        output = []
        errors = 0

        # XOR Data Whitening
        output, errors = self.apply_data_whitening(decoding, inpt)
        return output, errors

    def code_lsb_first(self, decoding, inpt):
        output = inpt.copy()
        errors = len(inpt) % 8

        # Change Byteorder to LSB first <-> LSB last
        i = 0
        while i < len(output) - 7:
            output[i + 0], output[i + 1], output[i + 2], output[i + 3], output[i + 4], output[i + 5], output[i + 6], \
            output[i + 7] = \
                output[i + 7], output[i + 6], output[i + 5], output[i + 4], output[i + 3], output[i + 2], output[i + 1], \
                output[i + 0]
            i += 8
        return output, errors

    def code_redundancy(self, decoding, inpt):
        output = []
        errors = 0

        if len(inpt) and self.multiple > 1:
            if decoding:
                # Remove multiple
                count = 0
                what = -1
                for i in inpt:
                    if i:
                        if not what:
                            if count > 0:
                                errors += 1
                            count = 0
                        what = True
                        count += 1
                        if (count >= self.multiple):
                            output.append(True)
                            count = 0
                    else:
                        if what:
                            if count > 0:
                                errors += 1
                            count = 0
                        what = False
                        count += 1
                        if (count >= self.multiple):
                            output.append(False)
                            count = 0
            else:
                # Add multiple
                for i in inpt:
                    output.extend([i] * self.multiple)
                    #if i:
                    #    output.extend([True] * self.multiple)
                    #else:
                    #    output.extend([False] * self.multiple)
        return output, errors

    def code_invert(self, decoding, inpt):
        errors = 0
        return [True if not x else False for x in inpt], errors

    def code_differential(self, decoding, inpt):
        output = [inpt[0]]
        errors = 0

        if decoding:
            # Remove differential from inpt stream
            i = 1
            while i < len(inpt):
                if inpt[i] != inpt[i - 1]:
                    output.append(True)
                else:
                    output.append(False)
                i += 1
        else:
            # Add differential encoding to output stream
            i = 1
            while i < len(inpt):
                if not inpt[i]:
                    output.append(output[i - 1])
                else:
                    if not output[i - 1]:
                        output.append(True)
                    else:
                        output.append(False)
                i += 1
        return output, errors

    def code_edge(self, decoding, inpt):
        errors = 0
        output = []

        if decoding:
            i = 1
            while i < len(inpt):
                if inpt[i] == inpt[i - 1]:
                    errors += 1
                    i += 1
                    continue
                output.append(inpt[i])
                i += 2
        else:
            for i in inpt:
                if not i:
                    output.extend([True, False])
                else:
                    output.extend([False, True])
        return output, errors

    def code_substitution(self, decoding, inpt):
        errors = 0
        output = []

        # Every element in src has to have the same size
        src = self.src
        dst = self.dst

        if len(src) < 1 or len(dst) < 1:
            return [[], 1]

        if not decoding:
            src, dst = dst, src

        minimum_item_size = len(src[0])
        # maximum_item_size = 0
        # for x in range(0, len(src)):
        #    if len(src[x]) < minimum_item_size:
        #        minimum_item_size = len(src[x])
        #    if len(src[x]) > maximum_item_size:
        #        maximum_item_size = len(src[x])

        i = 0
        while i < len(inpt):
            cnt = src.count(inpt[i:i + minimum_item_size])
            if cnt == 1:
                output.extend(dst[src.index(inpt[i:i + minimum_item_size])])
            elif cnt < 1:
                i += 1
                errors += 1
                continue
            # elif cnt > 1:
            #    for j in range(minimum_item_size, maximum_item_size):
            #        cnt = src.count(inpt[i:i+j])
            #        if cnt == 1:
            #            output.extend(dst[src.index(inpt[i:i+j])])
            #            i += j
            #            break
            #        elif cnt < 1:
            #            i += 1
            #            errors += 1
            #            break
            i += minimum_item_size

        return output, errors

    def code_externalprogram(self, decoding, inpt):
        errors = 0
        output = []

        if decoding and self.external_decoder != "":
            output = self.str2bit(self.run_command(self.external_decoder, self.bit2str(inpt)))
        elif not decoding and self.external_encoder != "":
            output = self.str2bit(self.run_command(self.external_encoder, self.bit2str(inpt)))
        else:
            print("Please set external de/encoder program!")
            return [[], 1]

        return output, errors

    def encode(self, inpt):
        return self.code(False, inpt)[0]

    def decode(self, inpt):
        return self.code(True, inpt)[0]

    def analyze(self, inpt):
        return self.code(True, inpt)[1]

    @staticmethod
    def bit2str(inpt, points=False):
        if not points:
            return "".join(["1" if x else "0" for x in inpt])
        else:
            bitstring = ""
            for i in range(0, len(inpt)):
                if i > 0 and i % 4 == 0:
                    bitstring += "."
                if inpt[i]:
                    bitstring += "1"
                else:
                    bitstring += "0"
            return bitstring

    @staticmethod
    def str2bit(inpt):
        return [True if x == "1" else False for x in inpt]

    @staticmethod
    def bit2hex(inpt):
        try:
            bitstring = "".join(["1" if x else "0" for x in inpt])
            # Better alignment
            if len(bitstring) % 4 != 0:
                bitstring += "0" * (4 - (len(bitstring) % 4))
            return hex(int(bitstring, 2))
        except (TypeError, ValueError) as e:
            pass
        return ""

    @staticmethod
    def hex2bit(inpt):
        if not isinstance(inpt, str):
            return []
        try:
            bitstring = bin(int(inpt, base=16))[2:]
            if len(bitstring) % 4 != 0:
                bitstring = "0" * (4 - (len(bitstring) % 4)) + bitstring
            return [True if x == "1" else False for x in bitstring]
        except (TypeError, ValueError) as e:
            pass
        return []

    @staticmethod
    def hex2str(inpt):
        bitstring = bin(int(inpt, base=16))[2:]
        return "0" * (4 * len(inpt.lstrip('0x')) - len(bitstring)) + bitstring


if __name__ == "__main__":
    e = encoding()
