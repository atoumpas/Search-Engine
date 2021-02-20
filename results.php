<?php
  session_start();
  function preprocessString($query) {
    #turn to lower case
    $new_query = mb_strtolower($query);

    #remove accents
    $accents = array('ά'=> 'α', 'έ' => 'ε', 'ό'=>'ο', 'ί' => 'ι', 'ή' => 'η', 'ύ' => 'υ', 'ώ' => 'ω');
    $new_query = strtr($new_query, $accents);

    #remove punctation
    $punctuation = [',','.','!','"','(',')',';',':','?','<','>','[',']','{','}','/','\\','\'','-','_','`','~','+',
      '*','=','@','#','$','%','^','&'];

    $new_query = str_replace($punctuation,'',$new_query);
    return $new_query;
  }


  function getRFQuery() {
    global $word_weights;
    $relevant_documents_weights = [];
    do {
      $json_string = file_get_contents("data/document_data.json");
      $documents = json_decode($json_string,true);
    } while($documents == NULL);
    if(!isset($_POST['feedback-pages'])) {    # if no relevant documents selected
      return;
    }
    $relevantIDs = $_POST['feedback-pages'];
    foreach($relevantIDs as $documentID) {
      $current_document = $documents[$documentID];
      $words = explode(" ", $current_document[3]);
      $tf = [];
      # count frequency of words in current document
      foreach($words as $word) {
        if(isset($tf[$word])) {
          $tf[$word] += 1;
        }
        else {
          $tf[$word] = 1;
        }
      }
      # add to document word weights vector
      foreach($tf as $word => $freq) {
        $log_freq = 1 + log($freq);
        if(isset($relevant_documents_weights[$word])) {
          $relevant_documents_weights[$word] += $log_freq;
        }
        else {
          $relevant_documents_weights[$word] = $log_freq;
        }
      }
    }
    foreach($relevant_documents_weights as $word => &$w) {
      #normalize and multiply by b = 0.8
      $w *= 0.8;
      $w /= count($relevantIDs);
      #add to original query weights
      if(isset($word_weights[$word])) {
        $word_weights[$word] += $w;
      }
      else {
        $word_weights[$word] = $w;
      }
    }
  }

  function files_exist() {
    if(file_exists("data/document_data.json") && file_exists("data/inverted_index.json") && file_exists("data/norms.json")) {
      return true;
    }
    return false;
  }

  function getTopResults($query) {
    global $word_weights;
    $search_words = "";
    if(empty($word_weights)) {
      $search_words = explode(" ", $query);
    }
    else {
      $search_words = array_keys($word_weights);
    }

    # send to json files to read from python script
    $file = fopen('data/query.json', 'w');
    fwrite($file, json_encode($search_words));
    fclose($file);

    # send to json files to read from python script
    $file = fopen('data/temp.json', 'w');
    $data['search'] = $search_words;
    $data['weights'] = $word_weights;
    fwrite($file, json_encode($data));
    fclose($file);

    exec('data/search_script.py '.$_POST['submit_button'].'');

    #connect to page database,get total number of pages
    do {
      $json_string = file_get_contents("data/document_data.json");
      $pages = json_decode($json_string,true);
    } while($pages == NULL);
    $N = count($pages);

    # connect to index
    do {
      $json_string = file_get_contents("data/inverted_index.json");
      $dictionary = json_decode($json_string,true);
    } while($dictionary == NULL);

    # connect to norms
    do {
      $json_string = file_get_contents("data/norms.json");
      $norms = json_decode($json_string,true);
    } while($norms == NULL);

    # initialize sums array
    $sum = [];

    # calculate sums
    foreach($search_words as $currect_word) {
      if(isset($dictionary[$currect_word])) { # if word exists in at least 1 document
        $tuples = $dictionary[$currect_word];
        $nt = count($tuples);
        $weight = 0;
        if($_POST['submit_button'] == 'search') { #if new search, weight = IDF
          $weight = log(1 + $N / $nt);
          $word_weights[$currect_word] = $weight; #update word weights in case of RF
        }
        else {              #weight given by relevance feedback calculations
          $weight = $word_weights[$currect_word];
        }
        foreach($tuples as $tuple) {
          $documentID = $tuple[0];
          $freq = $tuple[1];
          # if sum does not exist yet,create it
          if(!isset($sum[$documentID])) {
            $sum[$documentID] = 0;
          }
          $TF = 1 + log($freq);
          $sum[$documentID] += $TF * $weight;
        }
      }
      else {
        $word_weights[$currect_word] = 0; #give weight 0
      }
    }
    # normalize each accumulator
    foreach($sum as $ID => &$accumulator) {
      $accumulator /= $norms[$ID];
    }
    unset($accumulator);
    $_SESSION['word_weights'] = $word_weights;
    # get top-10 IDs
    arsort($sum);
    return array_keys(array_slice($sum, 0, 10, true));
  }

  function createPageContents($IDs,&$titles,&$URLS,&$descriptions) {
    # connect to page database, get title,URL and description for each top-10 ID
    do {
      $json_string = file_get_contents("data/document_data.json");
      $pages = json_decode($json_string,true);
    } while($pages == NULL);

    foreach($IDs as $currentID) {
      array_push($URLS,$pages[$currentID][0]);
      array_push($titles,$pages[$currentID][1]);
      array_push($descriptions,$pages[$currentID][2]);
    }
  }

  $search_string = "";
  if($_POST['submit_button'] == 'search') {
    $search_string = preprocessString($_POST['input']);
    $word_weights = [];
  }
  else {
    $word_weights = $_SESSION['word_weights'];
    $search_string = getRFQuery();
  }
  $titles = [];
  $URLS = [];
  $descriptions = [];

  if(files_exist()) {
    $IDs = getTopResults($search_string);
    createPageContents($IDs,$titles,$URLS,$descriptions);
  }
?>

<!doctype html>
<html lang="en">
	<head>
		<!-- Required meta tags -->
		<meta charset="utf-8">
		<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

		<!-- Bootstrap CSS -->
		<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css" integrity="sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh" crossorigin="anonymous">
		<title>Results for: <?php echo $_POST['input']?></title>

		<!-- My CSS file -->
		<link rel="stylesheet" type="text/css" href="results.css">
  </head>
  <body>
    <div class="container-fluid">
      <div class="top-side">
        <div class="form-row">
          <form id="search-form" action="results.php" method="post">
            <div class="row">
              <div class="input-group col-8">
                <input type="text" class="form-control" id="text-input" name="input" value="<?php echo $_POST['input'] ?>" placeholder="Type a string" required>
              </div>
              <div class="input-group col-2">
                <button type="submit" name="submit_button" value="search" class="btn btn-light"> Search </button>
              </div>
            </div>
          </form>
          <form id="update-form" action="results.php" method="post">
            <div class="row">
              <div class="input-group col-2">
                <input type="hidden" name="input" value="<?php echo $_POST['input'] ?>">
                <button type="submit" name="submit_button" value="update" class="btn btn-secondary"> Update </button>
              </div>
            </div>
          </form>
        </div>
      </div>
      <div class="bottom-side">
        <hr>
      <?php
      if(empty($titles)) {
        echo '<span> Your search for <b>"'.$_POST['input'].'"</b> did not match any documents. </span>';
      }
      else {
        echo '<span class="feedback-info"> Mark this page as relevant </span>';
      }
      for($i = 0; $i < count($titles); $i++) {
        echo '<div class="info-per-page">';
        echo '<div class="feedback">';
        echo '<div class="form-check">';
        echo '<input class="form-check-input" form="update-form" type="checkbox" name="feedback-pages[]" value="'.$IDs[$i].'">';
        echo '</div>';
        echo '</div>';

        echo '<div class="page-container">';
        echo '<span> '.$URLS[$i].'</span>';
        echo '<a href="'.$URLS[$i].'"> <h4>'.$titles[$i].'</h4> </a>';
        echo '<span>' .$descriptions[$i]. '</span>';
        echo '</div>';
        echo '</div>';
      }
      ?>
      </div>
      </form>
    </div>
    <!-- JavaScript Scripts -->
		<!-- jQuery first, then Popper.js, then Bootstrap JS -->
		<script src="https://code.jquery.com/jquery-3.4.1.slim.min.js" integrity="sha384-J6qa4849blE2+poT4WnyKhv5vZF5SrPo0iEjwBvKU7imGFAV0wwj1yYfoRSJoZ+n" crossorigin="anonymous"></script>
		<script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.0/dist/umd/popper.min.js" integrity="sha384-Q6E9RHvbIyZFJoft+2mJbHaEWldlvI9IOYy5n3zV9zzTtmI3UksdQRVvoxMfooAo" crossorigin="anonymous"></script>
		<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/js/bootstrap.min.js" integrity="sha384-wfSDF2E50Y2D1uUdj0O3uMBJnjuUD4Ih7YwaYd1iqfktj0Uod8GCExl3Og8ifwB6" crossorigin="anonymous"></script>
  </body>
</html>
