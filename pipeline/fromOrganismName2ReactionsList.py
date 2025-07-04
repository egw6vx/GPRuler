# -*- coding: utf-8 -*-
import os
import sys
import pandas as pd
import genericLib as gL
import GPRULERLib as gprL
import reactionsLib as rxnL
import bioservices.kegg as kegg

# setting working dirs
workingDirs = gL.setWorkingDirs()
OUTDIR = workingDirs[2]

model = input('Which is the model name? ')
organismChoice = input('Do you have the organism name (1) or the KEGG code (2) of the organism under investigation? ')
if organismChoice == '1':
    organism = input('Insert the organism name: ')
    dfPutativeOrgs = gprL.putativeOrganisms(organism)
    while len(dfPutativeOrgs) == 0:
        organism = input('Organism not found! Insert the organism name: ')
        dfPutativeOrgs = gprL.putativeOrganisms(organism)
    print('\nPutative organisms are:\n')
    for key, value in dfPutativeOrgs.items():
        print(key, '\t', value)
    print('\n')
    organismCode = input('Type the correct KEGG code among the returned ones: ')
elif organismChoice == '2':
    organismCode = input('Insert the KEGG organism code: ')

# Extract the entire list of genes of the target organism according to KEGG annotation
k = kegg.KEGG()
keggGenes = k.list(organismCode)
keggGenesSplt = keggGenes.strip().split("\n")
lOrganismGenes = []
for gene in keggGenesSplt:
    lOrganismGenes.append(gene.split('\t')[0].split(organismCode + ':')[1])

dGene2RxnsList = {}
cont = 1
geneFile = open(os.path.join(OUTDIR, model + '_GeneId2Rxns.csv'), mode='w')
gL.writeLineByLineToFile(geneFile, ['GeneId', 'Rxns'], '\t')

rxnFile = open(os.path.join(OUTDIR, model + '_RxnId2Equation.csv'), mode='w')
gL.writeLineByLineToFile(rxnFile, ['RxnId', 'Equation', 'Definition'], '\t')

rxn2EcFile = open(os.path.join(OUTDIR, model + '_RxnId2ECs.csv'), mode='w')
gL.writeLineByLineToFile(rxn2EcFile, ['RxnId', 'EC number'], '\t')

# Extract for each gene the list of catalysed reactions
dRxn2EcNumber = {}
dCompleteRxns_equation = {} # to save all the reactions candidate for the model avoiding duplicated elements (equation field of KEGG database)
dCompleteRxns_definition = {} # to save all the reactions candidate for the model avoiding duplicated elements (definition field of KEGG database)
for gene in lOrganismGenes:
    ## get for each gene its BRITE information in order to select only metabolic genes
    dizInfo, info = rxnL.getKeggInfo(organismCode + ':' + gene)
    lAssociatedRxns = []
    if 'BRITE' in dizInfo.keys() and 'Metabolism' in dizInfo['BRITE']:
        lOrths = list(dizInfo['ORTHOLOGY'].keys())
        for orth in list(dizInfo['ORTHOLOGY'].values()):
            posOpen = orth.find('[EC:')
            posClose = orth[posOpen:].find(']')
            ecNumber = orth[posOpen:posClose+posOpen+1][1:-1]
            lEcNumbers = list(gL.extractRegexFromItem(ecNumber, r"([0-9.-]+)")[0])
            if len(lEcNumbers) == 0:
                for orth in lOrths:
                    dizInfoOrth, infoOrth = rxnL.getKeggInfo('ko:' + orth)
                    if 'DBLINKS' in dizInfoOrth and 'RN' in dizInfoOrth['DBLINKS']:
                        lSelectedRxns = list(gL.extractRegexFromItem(dizInfoOrth['DBLINKS']['RN'], r"([A-Z0-9]+)")[0])
                        for rxnName in lSelectedRxns:
                            if rxnName not in dRxn2EcNumber:
                                dRxn2EcNumber[rxnName] = [orth]
                            else:
                                dRxn2EcNumber[rxnName] += [orth]

                            if rxnName.startswith('R') is True and rxnName not in dCompleteRxns_equation:
                                dizInfoRxn, infoRxn = rxnL.getKeggInfo('rn:' + rxnName)
                                if 'EQUATION' in dizInfoRxn.keys():
                                    rxnEquation = dizInfoRxn['EQUATION']
                                    rxnDefinition = dizInfoRxn['DEFINITION']
                                else:
                                    rxnEquation = ''
                                    rxnDefinition = ''

                                dCompleteRxns_equation[rxnName] = rxnEquation
                                dCompleteRxns_definition[rxnName] = rxnDefinition
                                gL.writeLineByLineToFile(rxnFile, [rxnName, rxnEquation, rxnDefinition], '\t')

                            if rxnName not in lAssociatedRxns:
                                lAssociatedRxns.append(rxnName)
            else:
                for ec in lEcNumbers:
                    dizInfoEc, infoEc = rxnL.getKeggInfo('ec:' + ec)
                    try:
                        if 'ALL_REAC' not in dizInfoEc.keys() and 'REACTION' in dizInfoEc.keys():
                            equazione = ' '. join(dizInfoEc['REACTION'])
                            eqSplt = equazione.split('=')
                            eqSplt_subs = eqSplt[0]
                            eqSplt_prods = eqSplt[1]
                            dSubs = gL.dizReaProd(eqSplt_subs)
                            dProds = gL.dizReaProd(eqSplt_prods)

                            lSubs = []
                            for s in dizInfoEc['SUBSTRATE']:
                                if 'CPD:' in s:
                                    pos = s.find('CPD:')
                                    substringa = s[pos + len('CPD:'):]
                                    lSubs += list(gL.extractRegexFromItem(substringa, r"([A-Z0-9]+)")[0])
                                else:
                                    lSubs += [s]

                            i = 0
                            dSubs_kegg = {}
                            for k, v in dSubs.items():
                                dSubs_kegg[lSubs[i]] = v
                                i += 1

                            lsubstratesParts = []
                            for k, v in dSubs.items():
                                lsubstratesParts.append(str(v) + ' ' + str(k))
                            substrates = ' + '.join(lsubstratesParts)

                            lsubstratesParts_kegg = []
                            for k, v in dSubs_kegg.items():
                                lsubstratesParts_kegg.append(str(v) + ' ' + str(k))
                            substrates_kegg = ' + '.join(lsubstratesParts_kegg)

                            lProds = []
                            for p in dizInfoEc['PRODUCT']:
                                if 'CPD:' in p:
                                    pos = p.find('CPD:')
                                    substringa = p[pos + len('CPD:'):]
                                    lProds += list(gL.extractRegexFromItem(substringa, r"([A-Z0-9]+)")[0])
                                else:
                                    lProds += [p]

                            i = 0
                            dProds_kegg = {}
                            for k, v in dProds.items():
                                dProds_kegg[lProds[i]] = v
                                i += 1

                            lproductsParts = []
                            for k, v in dProds.items():
                                lproductsParts.append(str(v) + ' ' + str(k))
                            products = ' + '.join(lproductsParts)

                            lproductsParts_kegg = []
                            for k, v in dProds_kegg.items():
                                lproductsParts_kegg.append(str(v) + ' ' + str(k))
                            products_kegg = ' + '.join(lproductsParts_kegg)

                            rxnName = 'R' + str(cont)
                            rxnEquation = substrates + ' <=> ' + products
                            rxnEquation_kegg = substrates_kegg + ' <=> ' + products_kegg

                            if rxnName not in dRxn2EcNumber:
                                dRxn2EcNumber[rxnName] = [ec]
                            else:
                                dRxn2EcNumber[rxnName] += [ec]

                            if rxnEquation not in dCompleteRxns_equation.values():
                                dCompleteRxns[rxnName] = rxnEquation_kegg
                                gL.writeLineByLineToFile(rxnFile, [rxnName, rxnEquation_kegg, rxnEquation], '\t')
                                cont += 1
                                lAssociatedRxns.append(rxnName)
                            else:
                                for k, v in dCompleteRxns_equation.items():
                                    if v == rxnEquation_kegg and k not in lAssociatedRxns:
                                        lAssociatedRxns.append(k)
                        elif 'ALL_REAC' in dizInfoEc.keys():
                            for rxn in dizInfoEc['ALL_REAC']:
                                if rxnName not in dRxn2EcNumber:
                                    dRxn2EcNumber[rxnName] = [ec]
                                else:
                                    dRxn2EcNumber[rxnName] += [ec]

                                lSelectedRxns = list(gL.extractRegexFromItem(rxn, r"([A-Z0-9]+)")[0])
                                for rxnName in lSelectedRxns:
                                    if rxnName.startswith('R') is True and rxnName not in dCompleteRxns:
                                        dizInfoRxn, infoRxn = rxnL.getKeggInfo('rn:' + rxnName)
                                        if 'EQUATION' in dizInfoRxn.keys():
                                            rxnEquation = dizInfoRxn['EQUATION']
                                            rxnDefinition = dizInfoRxn['DEFINITION']
                                        else:
                                            rxnEquation = ''
                                            rxnDefinition = ''

                                        dCompleteRxns_equation[rxnName] = rxnEquation
                                        dCompleteRxns_definition[rxnName] = rxnDefinition
                                        gL.writeLineByLineToFile(rxnFile, [rxnName, rxnEquation, rxnDefinition], '\t')

                                    if rxnName not in lAssociatedRxns:
                                        lAssociatedRxns.append(rxnName)
                    except:
                        for orth in lOrths:
                            dizInfoOrth, infoOrth = rxnL.getKeggInfo('ko:' + orth)
                            if 'DBLINKS' in dizInfoOrth and 'RN' in dizInfoOrth['DBLINKS']:
                                lSelectedRxns = list(gL.extractRegexFromItem(dizInfoOrth['DBLINKS']['RN'], r"([A-Z0-9]+)")[0])
                                for rxnName in lSelectedRxns:
                                    if rxnName not in dRxn2EcNumber:
                                        dRxn2EcNumber[rxnName] = [orth]
                                    else:
                                        dRxn2EcNumber[rxnName] += [orth]

                                    if rxnName.startswith('R') is True and rxnName not in dCompleteRxns_equation:
                                        dizInfoRxn, infoRxn = rxnL.getKeggInfo('rn:' + rxnName)
                                        if 'EQUATION' in dizInfoRxn.keys():
                                            rxnEquation = dizInfoRxn['EQUATION']
                                            rxnDefinition = dizInfoRxn['DEFINITION']
                                        else:
                                            rxnEquation = ''
                                            rxnDefinition = ''

                                        dCompleteRxns_equation[rxnName] = rxnEquation
                                        dCompleteRxns_definition[rxnName] = rxnDefinition
                                        gL.writeLineByLineToFile(rxnFile, [rxnName, rxnEquation, rxnDefinition], '\t')

                                    if rxnName not in lAssociatedRxns:
                                        lAssociatedRxns.append(rxnName)
    lAssociatedRxns = gL.unique(lAssociatedRxns)
    dGene2RxnsList[gene] = lAssociatedRxns
    gL.writeLineByLineToFile(geneFile, [gene, lAssociatedRxns], sep = '\t')
rxnFile.close()
geneFile.close()

for k, v in dRxn2EcNumber.items():
    gL.writeLineByLineToFile(rxn2EcFile, [k, v], sep = '\t')
rxn2EcFile.close()

# Generate the file including reaction to the corresponding catalysing genes list
flatdGene2RxnsList_values = [rxn for associatedRxns in dGene2RxnsList.values() for rxn in associatedRxns]
flatdGene2RxnsList_values = gL.unique(flatdGene2RxnsList_values)
outFile = open(os.path.join(OUTDIR, model + '_Rxns2Genes.csv'), mode='w')
gL.writeLineByLineToFile(outFile, ['Rxn', 'Genes'], '\t')
for r in flatdGene2RxnsList_values:
    lAssociatedGenes = []
    for k,v in dGene2RxnsList.items():
        if r in v and [k] not in lAssociatedGenes:
            lAssociatedGenes.append([k])
    lAssociatedGenes = gL.unique(lAssociatedGenes)
    gL.writeLineByLineToFile(outFile, [r, lAssociatedGenes], '\t')
outFile.close()
