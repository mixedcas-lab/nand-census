"""Offline tests: python3 -m unittest discover -s collector -v"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import classify as C  # noqa: E402


class TestRelevance(unittest.TestCase):
    def test_core(self):
        for t in ("A 1-Tb 4b/cell 4-Plane 162-Layer 3D Flash Memory With a 2.4-Gb/s I/O Speed Interface",
                  "A 512Gb 3b/cell 7th-Generation 3D-NAND Flash Memory with 184MB/s Write Throughput and 2.0Gb/s Interface",
                  "A 128 Gb 3b/cell V-NAND Flash Memory With 1 Gb/s I/O Rate",
                  "A Low-Power Page Buffer With Bit-Line Precharge Sharing",
                  "An LDPC Decoder With Soft-Decision Sensing for NAND Flash Storage",
                  "Lateral Migration of Trapped Electrons in Charge-Trap Flash Memory",
                  "Computing-in-Memory With 3D NAND Flash for Large Language Model Inference",
                  "Impact of Channel Poly-Si Grain Boundaries on Read Noise in 3-D NAND"):
            self.assertEqual(C.relevance(t, ""), "core", t)

    def test_not_nand(self):
        for t in ("A 6-bit 10-GS/s Flash ADC in 28-nm CMOS",
                  "A Two-Step Flash Converter With Background Calibration",
                  "Low-Power NAND Gate Design for Near-Threshold Logic",
                  "A 40-nm Embedded Flash Macro for Automotive MCUs",
                  "A NOR Flash Memory With 100-MHz Read for Code Storage",
                  "A Flash LiDAR Receiver With SPAD Array",
                  "A 12-bit SAR ADC"):
            self.assertIsNone(C.relevance(t, ""), t)

    def test_nand_named_beats_nor(self):
        self.assertEqual(C.relevance("NOR and NAND Flash Memory Scaling Challenges", ""), "core")

    def test_ssd_system_needs_nand_in_abstract(self):
        t = "A 16-Channel SSD Controller SoC With PCIe Gen5 Host Interface"
        self.assertIsNone(C.relevance(t, ""))
        self.assertEqual(C.relevance(t, "The controller manages 3D NAND packages over 16 channels."), "related")

    def test_abstract_only(self):
        self.assertEqual(C.relevance("A High-Voltage Charge Pump for Non-Volatile Memories",
                                     "The pump supplies program voltages for NAND flash memory."), "related")
        self.assertIsNone(C.relevance("A High-Voltage Charge Pump", "Used in a flash ADC reference."))


class TestTopics(unittest.TestCase):
    def test_chip_and_interface(self):
        tp = C.topics("A 1-Tb 4b/cell 4-Plane 162-Layer 3D Flash Memory With a 2.4-Gb/s I/O Speed Interface", "")
        self.assertIn("Chip", tp)
        self.assertIn("I/O interface", tp)

    def test_circuits(self):
        self.assertIn("Sensing/page buffer", C.topics("A Low-Power Page Buffer With Bit-Line Precharge Sharing", ""))
        self.assertIn("HV/WL driver", C.topics("A Word-Line Driver With Fast Ramp for 3D NAND", ""))
        self.assertIn("Controller/ECC/SSD", C.topics("An LDPC Decoder for NAND Flash Storage", ""))
        self.assertIn("Program/erase scheme", C.topics("An ISPP Program Scheme for QLC NAND", ""))
        self.assertIn("Compute/search", C.topics("Computing-in-Memory With 3D NAND Flash for LLM Inference", ""))

    def test_device_and_reliability(self):
        tp = C.topics("Lateral Migration of Trapped Electrons in Charge-Trap Flash Memory", "")
        self.assertIn("Device/cell", tp)
        self.assertIn("Reliability", tp)
        self.assertIn("Reliability", C.topics("Impact of Channel Poly-Si Grain Boundaries on Read Noise in 3-D NAND", ""))

    def test_abstract_adds_circuit_topics_not_chip(self):
        tp = C.topics("A 3D NAND Flash Memory", "We propose a page buffer for fast sensing. Prior 512Gb dies are compared.")
        self.assertIn("Sensing/page buffer", tp)
        self.assertEqual(tp.count("Chip"), 1)   # from the title only

    def test_order_is_stable(self):
        tp = C.topics("An LDPC Decoder and Page Buffer for a 1Tb NAND Chip", "")
        self.assertEqual(tp, [n for n, _ in C.TOPIC_RULES if n in tp])


class TestCompanies(unittest.TestCase):
    def test_companies(self):
        affs = ["Samsung Electronics, Hwaseong, South Korea", "SK hynix Inc., Icheon, South Korea",
                "KIOXIA Corporation, Yokohama, Japan", "Seoul National University, Seoul, South Korea"]
        self.assertEqual(C.companies(affs), ["Samsung", "SK hynix", "Kioxia/Toshiba"])

    def test_other_industry_only_alone(self):
        self.assertEqual(C.companies(["Foo Semiconductor Inc., Austin, TX, USA"]), ["Other industry"])
        self.assertEqual(C.companies(["Foo Inc., USA", "Micron Technology, Boise, ID, USA"]), ["Micron"])

    def test_org_and_country(self):
        self.assertEqual(C.org_and_country("Flash Design Team, Samsung Electronics, Hwaseong, South Korea"),
                         ("Samsung Electronics", "South Korea"))


def rec(num, title, pub, year=2025, abstract="", affs=("Samsung Electronics, Hwaseong, South Korea",), ctype="Conferences"):
    return {"article_number": num, "title": title, "publication_title": pub, "publication_year": year,
            "publication_date": "Feb. %d" % year, "abstract": abstract, "content_type": ctype, "doi": "10.1109/x.%d" % num,
            "authors": {"authors": [{"full_name": "A. Kim", "author_order": 1, "affiliation": list(affs)}]}}


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cache = os.path.join(self.tmp, "cache")
        os.makedirs(self.cache)
        self.data = os.path.join(self.tmp, "data")
        os.makedirs(self.data)
        self._paths = (build.PAPERS, build.META)
        build.PAPERS = os.path.join(self.data, "papers.json")
        build.META = os.path.join(self.data, "meta.json")
        self.config = build.load_json(build.CONFIG, None)

    def tearDown(self):
        build.PAPERS, build.META = self._paths
        shutil.rmtree(self.tmp)

    def put(self, r):
        with open(os.path.join(self.cache, "%s.json" % r["article_number"]), "w") as f:
            json.dump(r, f)

    def test_venues(self):
        v = self.config["venues"]
        self.assertEqual(build.venue_of("2024 IEEE International Memory Workshop (IMW)", v), "IMW")
        self.assertEqual(build.venue_of("2008 Joint Non-Volatile Semiconductor Memory Workshop and International Conference on Memory Technology and Design", v), "IMW")
        self.assertEqual(build.venue_of("2023 International Electron Devices Meeting (IEDM)", v), "IEDM")
        self.assertEqual(build.venue_of("IEEE Transactions on Electron Devices", v), "TED")
        self.assertEqual(build.venue_of("2025 IEEE International Solid-State Circuits Conference (ISSCC)", v), "ISSCC")
        self.assertIsNone(build.venue_of("IEEE Access", v))

    def test_rebuild(self):
        self.put(rec(1, "A 1Tb 4b/cell 280-Layer 3D NAND Flash Memory", "2025 IEEE International Solid-State Circuits Conference (ISSCC)"))
        self.put(rec(2, "A 8-bit Flash ADC", "2025 IEEE International Solid-State Circuits Conference (ISSCC)"))
        self.put(rec(3, "Read Disturb in Charge-Trap 3D NAND", "2024 IEEE International Memory Workshop (IMW)", 2024,
                     affs=("KIOXIA Corporation, Yokohama, Japan",)))
        self.put(rec(4, "A 3D NAND Flash Memory", "IEEE Access"))   # not a venue of this site
        self.put(rec(5, "Front Cover", "2025 IEEE International Solid-State Circuits Conference (ISSCC)"))
        meta = build.rebuild(self.config, self.cache, "2025-03-15")
        papers = build.load_json(build.PAPERS, [])
        self.assertEqual(sorted(p["id"] for p in papers), ["1", "3"])
        p1 = next(p for p in papers if p["id"] == "1")
        self.assertEqual((p1["v"], p1["lv"], p1["co"], p1["d"]), ("ISSCC", "core", ["Samsung"], "2025-02"))
        self.assertIn("Chip", p1["tp"])
        self.assertNotIn("abstract", json.dumps(papers))   # abstracts are never published
        self.assertEqual(meta["by_venue"], {"ISSCC": 1, "IMW": 1})
        self.assertEqual(meta["by_company"], {"Samsung": 1, "Kioxia/Toshiba": 1})
        self.assertEqual(meta["last_run_new"], 0)          # first build adds nothing "new"
        # a later build marks only newly cached recent papers as new
        self.put(rec(6, "An LDPC Decoder for QLC NAND Flash", "IEEE Journal of Solid-State Circuits", 2025, ctype="Journals"))
        meta = build.rebuild(self.config, self.cache, "2025-04-15")
        self.assertEqual(meta["last_run_new"], 1)
        p6 = next(p for p in build.load_json(build.PAPERS, []) if p["id"] == "6")
        self.assertEqual((p6["v"], p6["ct"], p6["first"]), ("JSSC", "J", "2025-04-15"))

    def test_empty_cache_keeps_old_data(self):
        self.put(rec(1, "A 1Tb 3D NAND Flash Memory", "2025 IEEE International Solid-State Circuits Conference (ISSCC)"))
        build.rebuild(self.config, self.cache, "2025-03-15")
        os.remove(os.path.join(self.cache, "1.json"))
        with self.assertRaises(SystemExit):
            build.rebuild(self.config, self.cache, "2025-04-15")
        self.assertEqual(len(build.load_json(build.PAPERS, [])), 1)


if __name__ == "__main__":
    unittest.main()
