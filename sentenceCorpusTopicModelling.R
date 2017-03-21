library(tm)
library(topicmodels)

setwd("~/MSPA/CSC-529/project/corpus")

#load files into corpus
#get the filenames to be loaded
filenames <- list.files(path=".",pattern = "*.txt")

#read lines from files
filetext <- lapply(filenames,readLines)

#create a corpus from the text read above
myCorpus <- Corpus(VectorSource(filetext))

#remove the commented lines of the form ### .... ###
removeComment <- function(x) gsub('### (abstract|introduction) ###','',x)
myCorpus <- tm_map(myCorpus,content_transformer(removeComment))

#remove the word placeholder CITATION/NUMBER
removePH <- function(x) gsub('(CITATION|NUMBER|SYMBOL)','',x)
myCorpus <- tm_map(myCorpus,content_transformer(removePH))

#remove punctuations
myCorpus <- tm_map(myCorpus,content_transformer(removePunctuation))

#check the text
writeLines(as.character(myCorpus[[1]]))
writeLines(as.character(myCorpus[[10]]))

#convert to lower case
myCorpus <- tm_map(myCorpus,content_transformer(tolower))

#remove digits if any
myCorpus <- tm_map(myCorpus,content_transformer(removeNumbers))

#convert different lines to one single paragraph
toSpace <- content_transformer(function(x, pattern) { return (gsub(pattern, " ", x))})
myCorpus <- tm_map(myCorpus,toSpace,"\\\n")

#Another text check
writeLines(as.character(myCorpus[[1]]))
#writeLines(as.character(myCorpus[[10]]),con="~/test.txt")

#remove stopwords
#myCorpus <- tm_map(myCorpus,removeWords,stopwords(kind="en"))
#writeLines(as.character(myCorpus[[10]]),con="~/MSPA/test.txt")

myStopwords = c("of","a","and","the","in","to","for","that","is","on","are","with","as","by","be","an",
                "which","it","from","or","can","have","these","has","such")
myCorpus <- tm_map(myCorpus,removeWords,myStopwords)
writeLines(as.character(myCorpus[[1]]))

myCorpus <- tm_map(myCorpus,stripWhitespace)

#stem documents
myCorpus <- tm_map(myCorpus,stemDocument)

myCorpus_tdm <- TermDocumentMatrix(myCorpus,control = list(weighting = "weightTfIdf"))
colnames(myCorpus_tdm) <- filenames

wordfreq <- rowSums(as.matrix(myCorpus_tdm))
length(wordfreq)
ord <- order(wordfreq,decreasing = TRUE)
wordfreq[ord]

write.csv(wordfreq[ord],"../word_freq.csv")

#perform LDA from topicmodels library
#determine optimal k with 10-fold cross validation
library(doParallel)
registerDoParallel(cores=3)
getDoParWorkers()

dtm <- DocumentTermMatrix(myCorpus)
seeds <- sample.int(10000,5)
nstart <- 5
best <- TRUE
em <- list(tol=10^-5)
var <- list(tol=10^-4)
splitfolds <- sample(1:10,30,replace = TRUE)
k_vals <- c(2,3,5,7,9,10,15,20,25,30,50)#,75,100,125,150,200,250,300)

results <- matrix(ncol=2,nrow=0)
colnames(results) <- c("k","perplexity")
for(k in k_vals) {
  results_k  <- matrix(ncol=2,nrow=0)
  colnames(results_k) <- c("k","perplexity")
  for(i in 1:10) {
    trainSet <- dtm[splitfolds != i,]
    testSet <- dtm[splitfolds == i,]
    ldaOutout <- LDA(trainSet,k=k,method = "VEM",control=list(nstart=5,
                                        seed=sample.int(10000,5),best=TRUE,em=list(tol=10^-5),
                                        var=list(tol=10^-4)))
    results_k <- rbind(results_k,c(k,perplexity(ldaOutout,newdata = testSet)))
  }
  results <- rbind(results,results_k)
}
rm(results_k,ldaOutout)
#Plot the perplexity vs. no of topics variation
library(ggplot2)
ggplot(data=as.data.frame(results), aes(x=k,y=perplexity)) + geom_point()+geom_smooth(se=FALSE) +
  xlab("No.of Topics")+theme_minimal()

# So we see that there is not much variation in the fit with no of topics extracted. So we will choose k=7 as 
#there are 7 sentence classification according to the AZ annotation scheme mentioned by the authors and then see 
#what we can discover and if we can make sense of them

library(ldatuning)
result <- FindTopicsNumber(dtm,topics=seq(2,200,1),method="VEM",
                           control=list(nstart=nstart,seed=seeds,best=best,em=em,var=var),
                           mc.cores = 3,verbose = TRUE)

# we will create 3 models, one with VEM_alpha_estimated, VEM_alpha_fixed and Gibbs_beta_estimated
# and compare the results
k <- 7
seeds <- sample.int(10000,5)
nstart <- 5
best <- TRUE
em <- list(iter.max=1000,tol=10^-5)
init <- "seeded" # Choosing this you will see some output on screen like "initialized with doc...." which is creating seedwords

lda_vem_est_all <- LDA(dtm,k,method="VEM",control=list(nstart=nstart,seed=seeds,best=best,em=em,initialize=init))

topics_vem_est_all <- topics(lda_vem_est_all)
terms_vem_est_all <- terms(lda_vem_est_all,10)
prob_vem_est_all <- lda_vem_est_all@gamma


lda_vem_fix_alpha <- LDA(dtm,k,method="VEM",control=list(nstart=nstart,seed=seeds,best=best,em=em,alpha=7,
                                                         estimate.alpha=FALSE))
topics_vem_fix_alpha <- topics(lda_vem_fix_alpha)
terms_vem_fix_alpha <- terms(lda_vem_fix_alpha,10)
prob_vem_fix_alpha <- lda_vem_fix_alpha@gamma

burnin <- 4000
iter <- 2000
thin <- 500
lda_gibbs <- LDA(dtm,k,method="Gibbs",control = list(nstart=nstart,seed=seeds,iter=iter,burnin=burnin,thin=thin,
                                                      best = best))
topics(lda_gibbs)
terms(lda_gibbs,10)

lda_gibbs@gamma

#plot the probability of assignment to most likely topic
prob_most_likely_topic <- as.data.frame(table(round(apply(prob_vem_est_all,1,FUN=max),digits=1)))
prob_most_likely_topic$Algo <- "VEM"
aa <- as.data.frame(table(round(apply(prob_vem_fix_alpha,1,FUN=max),digits=1)))
aa$Algo <- "VEM_Alpha_fixed"
prob_most_likely_topic <- rbind(prob_most_likely_topic,aa)
rm(aa)
aa <- as.data.frame(table(round(apply(lda_gibbs@gamma,1,FUN=max),digits=1)))
aa$Algo <- "Gibbs"
prob_most_likely_topic <- rbind(prob_most_likely_topic,aa)
rm(aa)

ggplot(data=prob_most_likely_topic,aes(Var2,Freq,fill=Algo))+geom_bar(stat="identity",position = "dodge")+
  scale_fill_brewer(type = "qual",palette = 3)+facet_grid(Algo ~ .)+expand_limits(xmin=0,xmax=1)+theme_minimal()+
  labs(x="Probability of assignment to most likely topic",y="No of documents")
