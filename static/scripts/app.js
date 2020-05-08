class Session {
  constructor() {
    this.base_url = '/api/likes'
  }

  async addLikes(userId, messageId) {
    try {
      const response = await axios.post(
        this.base_url, {user_id: userId, message_id: messageId}
      );
      return response.data.likes;
    } catch (error) {
      axiosErrorHandler(error);
    }
    return null;
  }

  async removeLikes(likesId) {
    try {
      const response = await axios.delete(`${this.base_url}/${likesId}`);
      return response.data.message;
    } catch (error) {
      axiosErrorHandler(error);
    }
    return null;
  }
}


function axiosErrorHandler(error) {
  if (error.response) {
    // The request was made and the server responded with a status code
    // that falls out of the range of 2xx
    console.log(error.response.data);
    console.log(error.response.status);
    console.log(error.response.headers);
  } else if (error.request) {
    // The request was made but no response was received
    // `error.request` is an instance of XMLHttpRequest in the browser and an instance of
    // http.ClientRequest in node.js
    console.log(error.request);
  } else {
    // Something happened in setting up the request that triggered an Error
    console.log('Error', error.message);
  }
  console.log(error.config);
}


$(async function(){
  const $messages = $('#messages');
  const session = new Session();

  $messages.on('submit', '.messages-form', async function(event){
    event.preventDefault();

    console.log('Like submitted')
    if ($(this).data("likes-id")) {
      const likesId = $(this).data("likes-id");
      await session.removeLikes(likesId);
      // remove likes-id flag
      $(this).removeAttr("data-likes-id");
      $(this).removeData("likes-id");
      // update icon to be solid
      const $likeBtn = $(this).find('button');
      $likeBtn.children().remove();
      $likeBtn.append('<i class="far fa-thumbs-up"></i>');
    } else {
      const messageId = $(this).data("message-id");
      const userId = $(this).data("user-id");
      const resp = await session.addLikes(userId, messageId);
      // add likes-id flag
      $(this).attr("data-likes-id", resp.id);
      $(this).data("likes-id", resp.id)
      // update icon to be solid
      const $likeBtn = $(this).find('button');
      $likeBtn.children().remove();
      $likeBtn.append('<i class="fas fa-thumbs-up"></i>');
    }
  })

});