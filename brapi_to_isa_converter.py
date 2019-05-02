from isatools.model import Investigation, OntologyAnnotation, OntologySource, Assay, Study, Characteristic, Source, \
    Sample, Comment, Person

from pycountry_convert import country_alpha3_to_country_alpha2 as a3a2
import copy
from collections import defaultdict
from brapi_client import BrapiClient

def att_test(attribute):
    if attribute:
        return attribute
    else:
        return "NA"

class BrapiToIsaConverter:
    """ Converter json coming out of the BRAPI to ISA object

    ..warning: you may want to tweak this class name
    ..warning: some methods may never be called by the main:
        - create_isa_investigation()
        - create_germplasm_chars()
        - create_materials()
    """

    def __init__(self, logger, endpoint):
        self.logger = logger
        self.endpoint = endpoint
        self._brapi_client = BrapiClient(self.endpoint, self.logger)

    # _brapi_client
    #
    # def get_brapi_client(self) -> BrapiClient:
    #     if self._brapi_client is None:
    #
    #     return self._brapi_client
    def get_obs_levels(self, brapi_study_id):
        # because not every obs level has the same variables, and this is not yet supported by brapi to filter on /
        # every observation will be checked for
        obs_level_in_study = defaultdict(set)
        obs_levels = defaultdict(set)
        for ou in self._brapi_client.get_study_observation_units(brapi_study_id):
            for obs in ou['observations']:
                if ou['observationLevel']:
                    obs_level_in_study[ou['observationLevel']].add(
                        obs['observationVariableName'])
                    if 'observationLevels' in ou.keys() and ou['observationLevels']:
                        for obslvl in ou['observationLevels'].split(","):
                            a, b = obslvl.split(":")
                            obs_levels[ou['observationLevel']].add(a)
                else:
                    obs_level_in_study['study'].add(
                        obs['observationVariableName'])

        self.logger.info("Observation Levels in study: " +
                         ",".join(obs_level_in_study.keys()))
        return obs_level_in_study, obs_levels

    def create_germplasm_chars(self, germplasm):
        """" Given a BRAPI Germplasm ID, retrieve the list of all attributes from BRAPI and returns a list of ISA
        characteristics using MIAPPE tags for compliance + X-check against ISAconfiguration"""
        # TODO: switch BRAPI tags to MIAPPE Tags

        returned_characteristics = []

        germplasm_id = germplasm['germplasmDbId']
        all_germplasm_attributes = self._brapi_client.get_germplasm(
            germplasm_id)

        mapping_dictionnary = {
            "accessionNumber": "Material Source ID",
            "commonCropName": "commonCropName",
            "genus": "Genus",
            "species": "Species",
            "subtaxa": "Infraspecific Name",
            "taxonIds": ["Organism", "sourceName", "taxonId"]

        }

        for key in all_germplasm_attributes.keys():

            if key in mapping_dictionnary.keys():
                if isinstance(mapping_dictionnary[key], str):
                    c = self.create_isa_characteristic(
                        mapping_dictionnary[key], str(all_germplasm_attributes[key]))
                else:
                    if all_germplasm_attributes[key] and len(all_germplasm_attributes[key]) > 0:
                        taxinfo = []
                        for item in range(len(all_germplasm_attributes[key])):
                            taxinfo.append(all_germplasm_attributes[key][item][mapping_dictionnary[key][1]] + ":" +
                                           all_germplasm_attributes[key][item][mapping_dictionnary[key][2]])
                        ontovalue = ";".join(taxinfo)
                        c = self.create_isa_characteristic(
                            mapping_dictionnary[key][0], ontovalue)
                        if c not in returned_characteristics:
                            returned_characteristics.append(c)

            elif key == "donors":
                miappeKey = "Donors"
                donors = []
                for item in range(len(all_germplasm_attributes["donors"])):
                    donors.append(att_test(all_germplasm_attributes[key][item]["donorInstituteCode"]) + ":" +
                                  att_test(all_germplasm_attributes[key][item]["donorAccessionNumber"]))
                ontovalue = ";".join(donors)
                c = self.create_isa_characteristic(miappeKey, ontovalue)

            elif key == "synonyms":
                if isinstance(all_germplasm_attributes[key], list):
                    ontovalue = ";".join(all_germplasm_attributes[key])
                    c = self.create_isa_characteristic(key, ontovalue)

            else:
                c = self.create_isa_characteristic(
                    key, str(all_germplasm_attributes[key]))

            if c not in returned_characteristics:
                returned_characteristics.append(c)

        return returned_characteristics

    # def create_isa_investigations(self, endpoint):
    #     """Create ISA investigations from a BrAPI endpoint, starting from the trials information"""

    #     endpoint_investigations = []
    #     for this_trial in self._brapi_client.get_brapi_trials():
    #         this_investigation = Investigation()
    #         this_investigation.identifier = this_trial['trialDbId']
    #         this_investigation.title = this_trial['trialName']
    #         # investigation.comments.append(Comment("Investigation Start Date", trial['startDate']))
    #         # investigation.comments.append(Comment("Investigation End Date", trial['endDate']))
    #         # investigation.comments.append(Comment("Active", trial['active']))

    #         for this_study in this_trial['studies']:
    #             this_study = self.create_isa_study(this_study['studyDbId'])
    #             this_investigation.studies.append(this_study)
    #             endpoint_investigations.append(this_investigation)
    #     return endpoint_investigations

    # def create_materials(self, endpoint):
    #     """Create ISA studies from a BrAPI endpoint, starting from the studies, where there is no trial information."""

    #     for phenotype in self._brapi_client.get_phenotypes():
    #         print(phenotype)
    #         # for now, creating the sample name combining studyDbId and potDbId -
    #         # eventually this should be observationUnitDbId
    #         sample_name = phenotype['studyDbId'] + "_" + phenotype['plotNumber']
    #         this_sample = Sample(name=sample_name)
    #         that_source = Source(phenotype['germplasmName'], phenotype['germplasmDbId'])
    #         this_sample.derives_from = that_source

        # for level in obs_levels_in_study:
        #     oref_mt = OntologySource(name="OBI", description="Ontology for Biomedical Investigation")
        #     oa_mt = OntologyAnnotation(term="phenotyping", term_accession="", term_source=oref_mt)
        #     oref_tt = OntologySource(name="OBI", description="Ontology for Biomedical Investigation")
        #     oa_tt = OntologyAnnotation(term="multimodal technique", term_accession="", term_source=oref_tt)
        #     isa_assay_file = "a_" + str(brapi_study_id) + "_" + level + ".txt"
        #     new_assay = Assay(measurement_type=oa_mt, technology_type=oa_tt, filename=isa_assay_file)
        #     isa_study.assays.append(new_assay)
        #     if oref_mt not in isa_investigation.ontology_source_references:
        #         isa_investigation.ontology_source_references.append(oref_mt)
        #     if oref_tt not in isa_investigation.ontology_source_references:
        #         isa_investigation.ontology_source_references.append(oref_tt)

        # return isa_study, isa_investigation

    def create_isa_study(self, brapi_study_id, investigation, obs_levels_in_study):
        """Returns an ISA study given a BrAPI endpoints and a BrAPI study identifier."""

        brapi_study = self._brapi_client.get_study(brapi_study_id)

        this_study = Study(filename="s_" + str(brapi_study_id) + ".txt")

        this_study.identifier = brapi_study.get('studyDbId', "NA")

        if 'name' in brapi_study:
            this_study.title = brapi_study['name']
        elif 'studyName' in brapi_study:
            this_study.title = brapi_study['studyName']
        else:
            this_study.title = "NA"

        this_study.description = att_test(brapi_study.get('studyDescription', "NA"))
        this_study.comments.append(Comment(name="Study Start Date", value=att_test(brapi_study.get('startDate', "NA"))))
        this_study.comments.append(Comment(name="Study End Date", value=att_test(brapi_study.get('endDate', "NA"))))
        this_study.comments.append(Comment(name="Study Experimental Site", value=att_test(brapi_study['location'].get('name', "NA"))))

        if 'countryCode' in brapi_study['location'] and brapi_study['location']['countryCode']:
            if len(brapi_study['location']['countryCode']) == 3:
                this_study.comments.append(Comment(name="Study Country",
                                                   value=a3a2(brapi_study['location']['countryCode'])))
            elif len(brapi_study['location']['countryCode']) == 2:
                this_study.comments.append(Comment(name="Study Country",
                                                   value=brapi_study['location']['countryCode']))
        elif 'countryName' in brapi_study['location'] and brapi_study['location']['countryName']:
            this_study.comments.append(Comment(name="Study Country",
                                               value=brapi_study['location']['countryName']))
        else:
            this_study.comments.append(
                Comment(name="Study Country", value="NA"))

        this_study.comments.append(Comment(name="Study Latitude", value=att_test(brapi_study['location'].get('latitude', "NA"))))
        this_study.comments.append(Comment(name="Study Longitude", value=att_test(brapi_study['location'].get('longitude', "NA"))))
        this_study.comments.append(Comment(name="Study Altitude",value=att_test(brapi_study['location'].get('altitude', "NA"))))

        study_design = att_test(brapi_study.get('studyType', "NA"))
        oa_st_design = OntologyAnnotation(term=study_design)
        this_study.design_descriptors = [oa_st_design]


        if 'contacts' in brapi_study:
            for brapicontact in brapi_study['contacts']:
                #NOTE: brapi has just name atribute -> no seperate first/last name
                ContactName = brapicontact['name'].split(' ')
                contact = Person(first_name=ContactName[0], last_name=ContactName[1],
                affiliation=brapicontact['institutionName'], email=brapicontact['email'])
                this_study.contacts.append(contact)

        this_study.comments.append(Comment(name="Trait Definition File", value="t_" + str(brapi_study_id) + ".txt"))
        
        if 'dataLinks' in brapi_study:
            for brapidata in brapi_study['dataLinks']:
                this_study.comments.append(Comment(name="Study Data File Link",value=brapidata['url']))
                this_study.comments.append(Comment(name="Study Data File Description",value=brapidata['type']))
                this_study.comments.append(Comment(name="Study Data File Version",value="NA"))

        # Declaring as many ISA Assay Types as there are BRAPI Observation Levels
        ###########################################################################
        for level in obs_levels_in_study:

            oref_mt = OntologySource(
                name="OBI", description="Ontology for Biomedical Investigation")
            oa_mt = OntologyAnnotation(
                term="phenotyping", term_accession="", term_source=oref_mt)
            oref_tt = OntologySource(
                name="OBI", description="Ontology for Biomedical Investigation")
            oa_tt = OntologyAnnotation(
                term=level + " multimodal technique", term_accession="", term_source=oref_tt)
            isa_assay_file = "a_" + str(brapi_study_id) + "_" + level + ".txt"
            new_assay = Assay(measurement_type=oa_mt,
                              technology_type=oa_tt, filename=isa_assay_file)
            new_assay.characteristic_categories.append(level)

            this_study.assays.append(new_assay)

            if oref_mt not in investigation.ontology_source_references:
                investigation.ontology_source_references.append(oref_mt)
            if oref_tt not in investigation.ontology_source_references:
                investigation.ontology_source_references.append(oref_tt)

        print("number of ISA assays:", len(this_study.assays))

        return this_study, investigation

    def create_isa_characteristic(self, my_category, my_value):
        """Given a pair of category and value, return an ISA Characteristics element """
        this_characteristic = Characteristic(category=OntologyAnnotation(term=str(my_category)),
                                             value=OntologyAnnotation(term=str(my_value), term_source="",
                                                                      term_accession=""))

        return this_characteristic

    def create_isa_tdf_from_obsvars(self, obsvars):
        records = []
        header_elements = ["Variable Name", "Variable Full Name", "Variable Description", "Crop", "Growth Stage",
                           "Date",
                           "Method", "Method Description", "Method Formula", "Method Reference", "Scale",
                           "Scale Data Type",
                           "Scale Valid Values", "Unit", "Trait Name", "Trait Term REF", "Trait Class", "Trait Entity",
                           "Trait Attribute"]

        tdf_header = '\t'.join(header_elements)
        records.append(tdf_header)

        for obs_var in obsvars:
            record_element = [str(obs_var['name']), str(obs_var['ontologyDbId']), str(obs_var['ontologyName']),
                              str(obs_var['crop']),
                              str(obs_var['growthStage']), str(
                                  obs_var['date']), str(obs_var['method']['name']),
                              str(obs_var['method']['description']), str(
                                  obs_var['method']['formula']),
                              str(obs_var['method']['reference']), str(
                                  obs_var['scale']['name']),
                              str(obs_var['scale']['dataType']),
                              str(obs_var['scale']['validValues']['categories']), str(
                                  obs_var['scale']['xref']),
                              str(obs_var['trait']['name']), str(
                                  obs_var['trait']['xref']),
                              str(obs_var['trait']['class']),
                              str(obs_var['trait']['entity']), str(obs_var['trait']['attribute'])]

            record = '\t'.join(record_element)
            records.append(record)

        return records

    def create_isa_obs_data_from_obsvars(self, obs_units, obs_variables, level, germplasminfo, obs_levels):
        data_records = []
        obs_levels_header = []
        for obslvl in obs_levels[level]:
            obs_levels_header.append("observationLevels[{}]".format(obslvl))
        # headers belonging observation unit
        obs_unit_header = ["observationUnitDbId", "observationUnitXref",
                           "X", "Y", "germplasmDbId", "germplasmName"]
        # headers belonging germplasm
        germpl_header = ["accessionNumber"]
        # headers belonging observation
        obs_header = ["season", "observationTimeStamp"]
        # adding variables headers
        head = obs_levels_header + obs_unit_header + \
            germpl_header + obs_header + obs_variables

        datafile_header = '\t'.join(head)
        data_records.append(datafile_header)

        emptyRow = []  # Empty row that is later filled in with values -> fixed row size
        for i in range(len(head)):
            emptyRow.append("")

        for obs_unit in obs_units:
            if obs_unit['observationLevel'] == level:
                row = copy.deepcopy(emptyRow)
                # Get data from observationUnit
                for obs_unit_attribute in obs_unit.keys():
                    if obs_unit_attribute == "observationLevels" and obs_unit['observationLevels']:
                        # NOTE: INRA specific
                        for obslvls in obs_unit['observationLevels'].split(","):
                            a, b = obslvls.split(":")
                            row[head.index(
                                "observationLevels[{}]".format(a))] = b
                    if obs_unit_attribute in obs_unit_header and obs_unit[obs_unit_attribute]:
                        outp = []
                        if obs_unit_attribute == "observationUnitXref":
                            # NOTE: INRA specific
                            for item in obs_unit[obs_unit_attribute]:
                                if item["id"]:
                                    outp.append("{!s}:{!r}".format(
                                        item["source"], item["id"]))
                            row[head.index("observationUnitXref")
                                ] = ';'.join(outp)
                        else:
                            row[head.index(obs_unit_attribute)
                                ] = obs_unit[obs_unit_attribute]
                        if obs_unit_attribute == "germplasmDbId":
                            row[head.index(
                                "accessionNumber")] = germplasminfo[obs_unit[obs_unit_attribute]][0]

                rowbuffer = copy.deepcopy(row)

                for measurement in obs_unit['observations']:
                    # Get data from observation
                    for obs_attribute in obs_header:
                        if obs_attribute in measurement and measurement[obs_attribute]:
                            row[head.index(obs_attribute)
                                ] = measurement[obs_attribute]
                        else:
                            self.logger.info(
                                obs_attribute + " does not exist in observation in observationUnit " + obs_unit['observationUnitDbId'])
                    if measurement["observationVariableName"] in head:
                        row[head.index(measurement["observationVariableName"])] = str(
                            measurement["value"])
                        data_records.append('\t'.join(row))
                        row = copy.deepcopy(rowbuffer)
                    else:
                        self.logger.info(
                            measurement["observationVariableName"] + " does not exist in observationVariable list ")

        return data_records
